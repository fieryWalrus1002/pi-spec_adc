import argparse
import csv
import io
import logging
import math
import random
import time
from datetime import datetime
from pathlib import Path
from sys import exit
from time import sleep

import pandas as pd
import serial
import serial.tools.list_ports

# ttyACM0 Seeeduino
# ttyUSB0 MX3
# class DataLogger():
#     def __init__(self):
#           # initalize the class
# class DataDaemon(Thread):
#     def __init__(self, window):
#         Thread.__init__(self)
#         # self.stopped = Event()
#         self.parent = window

#     def run(self):
#         while True:
#             # check the buffer every quarter second
#             time.sleep(0.25)
#             self.parent.check_buffer()


class DataLogger:
    def __init__(self, timeout: float = 1.0):
        self.adc = None
        self.packet_size = 1000
        self.connect_adc(timeout=timeout)
        self.data = []
        self.df = None

    def connect_adc(self, timeout: float = 1.0):
        """creates serial connection to ADC device"""
        # ttyACM0 Seeeduino, vid 10374, pid 32815
        for port in serial.tools.list_ports.comports():
            if port.vid == 10374:
                device = port.device

        while self.adc is None:
            logging.debug("connecting to ADC")
            self.adc = serial.Serial(device, 4000000, timeout=timeout)

            if self.adc is None:
                sleep(1)

        logging.debug(f"ADC connected, timeout= {timeout}")

    def close_connection(self):
        self.adc.close()

    def flush_buffer(self):
        self.adc.reset_input_buffer()

    def send_command(self, cmd_input, value):
        cmd_output = cmd_input + str(value) + ";"
        self.adc.write(cmd_output.encode("utf-8"))

    def query(self):
        self.send_command(cmd_input="s", value=0)
        recv = ""

        while self.adc.inWaiting() > 0:
            recv += self.adc.readline().decode("utf-8")
        return recv

    def listen_for_response(self):
        recv = ""
        while self.adc.inWaiting() > 0:
            recv += self.adc.readline().decode("utf-8")
        return recv

    def ready_scan(self, num_points):
        # send a command to the adc to prepare a scan with the given number of points
        self.send_command("r", num_points)

    def change_adc_channel(self, channel):
        print("change_adc_channel not a valid command")
        pass

    def get_data_old(self, num_points, test=0, **kwargs):
        packet_size = kwargs.get(
            "packet_size", 500
        )  # either use this many points or whatever is specified in kwargs

        # get the data between 0 and num_points in a number of packets equal to the class variable packet_size

        # wait for the ADC to be ready to send over data
        data = []
        resp = ""
        i = 0

        while (resp == "") and (i < 10):
            time.sleep(0.25)
            resp = self.listen_for_response()

        print("Data ready for retrieval: %s ." % resp)

        # measure how much time it takes to get the data back
        begin = datetime.now()

        # how many packets are we requesting? round up to the next integer
        total_packets = math.ceil(num_points / packet_size)

        # for each packet we get, add it to the packet_list
        packet_list = []

        # get data for each packet
        for packet in range(0, total_packets):
            # send get data command
            self.send_command("g", packet_size)

            # receive the data
            packet_list.append(self.adc.read_until(";").decode("utf-8").split("\r"))

        # how long did it take?
        time_elapsed = datetime.now() - begin
        print("time elapsed: %f " % time_elapsed)

        # combine all the data from packets to a data file
        for packet in packet_list:
            for row in packet:
                data.append(row)

        print("recv data, length: %i, expected: %i" % len(data), num_points)

        return data

    def parse_raw(raw):
        """parse bytes output from Arduino"""
        raw = raw.decode()
        if raw[-1] != "\n":
            raise ValueError(
                "Input must end with newline, otherwise message is incomplete"
            )

        t, V = raw.rstrip().split(",")

        return int(t), int(V) * 3.3 / 4095

    # def read_all(
    #     self, read_buffer=b"",
    # ):
    #     """ read all available bytes from the serial port and append to read buffer"""

    #     previous_timeout = self.adc.timeout
    #     self.adc.timeout = None

    #     in_waiting = self.adc.in_waiting
    #     read = self.adc.read(size=in_waiting)

    #     self.adc.timeout = previous_timeout

    #     return read_buffer + read

    # def get_data(self, num_points: int = 10, test: int = 0):
    #     buffer = b""

    #     self.send_command("g", num_points)

    #     buffer = self.read_all(read_buffer=buffer)

    #     logging.debug("buffer read")
    #     return buffer

    def get_data(self, num_points: int = 10, test: int = 0):
        data = []

        self.send_command("g", num_points)

        for _ in range(num_points):

            raw = self.adc.read_until(";",).decode("utf-8")
            data.append(raw)
            # try:
            #     t, V = parse_raw(raw)
            #     point[i] = t
            #     voltage[i] = V
            # except:
            #     pass

        return data

    def save_data_to_csv(self, trace_data, trace_params, trace_num):
        wl = str(trace_params.meas_led_vis) + str(trace_params.meas_led_ir)
        trace_date = time.strftime("%d%m%y")
        trace_time = time.strftime("%H%M")

        if trace_params.trace_note == "":
            trace_note = ""
        else:
            trace_note = str(trace_params.trace_note) + "_"

        export_path = (
            "./export/"
            + trace_date
            + "_"
            + trace_time
            + "_"
            + wl
            + "_"
            + trace_note
            + str(trace_num)
        )
        trace_filename = export_path + ".csv"

        # make the directory if it doesn't exist already
        Path("./export/").mkdir(parents=True, exist_ok=True)

        # write the data for this trace to disk
        with open(trace_filename, "a") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(["trace_params", trace_params.parameter_string])
            writer.writerow(["num", "voltage"])

            for row in trace_data:
                writer.writerow(row.split(","))
                # time.sleep(.001)

        f.close()

        return trace_filename

    def print_data(self, data):
        for row in data:
            print(row)

    def test_data_retrieval(self, num_points):
        print(f"adc.timeout: {self.adc.timeout}")

        # logging.debug("generate test data")
        # self.send_command(cmd_input="t", value=1000)

        logging.debug("getting data")
        data = self.get_data(num_points=num_points)
        logging.debug(f"data acquired: {data}")
        self.print_data(data)

    def read(self):
        return self.adc.read_until()

    # if __name__ == "__main__":

    #     # try:
    #     #     adc = serial.Serial('/dev/ttyACM0', 4000000, timeout=5)
    #     # except:
    #     #         print('adc fail')

    #     for port in serial.tools.list_ports.comports():
    #         if port.vid == 10374:
    #             device = port.device
    #     try:
    #         datalogger = DataLogger(serial.Serial(device, 4000000, timeout=1))

    #     except:
    #         print("No XIAO device found.")

    #     print(f"XIAO connected at {device}")

    #     # datalogger.test(100)
    #     recv_data = datalogger.get_data(1000, test=0)
    #     print(len(recv_data), 1000)
    #     for row in recv_data:
    #         print(row)

    def read_line(self):
        return self.adc.read_until().decode("utf-8").split("\r")[0]

    def get_state(self):
        self.send_command("r", 0)
        return self.read_line()

    def toggle_state(self):
        self.send_command("t", 0)

    def retrieve_data(self, timeout: float = 2.0):
        """tries to retrieve data from XIAO devicem, timeout is in seconds"""
        data = []
        elapsed_time = 0
        sleep_time = timeout / 100

        while elapsed_time < timeout:
            if self.data_ready():
                data.append(self.adc.read_until().decode())
            elapsed_time += sleep_time
            sleep(sleep_time)

        return data

    def data_ready(self) -> bool:
        if self.adc.in_waiting > 0:
            return True
        else:
            return False

    def flush_buffer(self) -> None:
        self.adc.flushInput()
        self.adc.flushOutput()

    def trigger_adc(self, timeout):
        self.send_command("t", 1)
        data = []
        for attempt in range(0, 2):
            data += self.retrieve_data(timeout=timeout)
        return data

    def process_data(self, raw_data) -> None:
        data_list = []

        def value_to_voltage(value) -> float:
            return round(int(value) / 4095 * 3.3, 4)

        for row in raw_data:
            # datas_list.append(value_to_voltage(row))
            try:
                idx, micros, value = row[:-2].split(",")
                if value is not None:
                    voltage = value_to_voltage(value)
                    data_list.append([int(idx), int(micros), voltage])
            except ValueError:
                pass

        df = pd.DataFrame(data_list, columns=["idx", "time_us", "voltage"])

        # df["time_us"] = df["time_us"] - df["time_us"][0]
        # df = pd.DataFrame(data_list, columns=["voltage"])

        return df

    def print_data(self, df):
        print(df)
        print(f"len:df= {len(df)}")

    def get_user_input(self) -> str:
        print("'l' to set capture_limit to 100")
        print("'t' to trigger ADC")
        print("'p' to print data")
        print("'q' to quit")

        cmd_input = input("enter command: ")

        return cmd_input

    def process_user_input(self, cmd_input, capture_limit):
        if cmd_input == "l":
            self.send_command("l", 100)
            data = []
            timeout = capture_limit / 100
            print(f"capture_limit: {capture_limit}, timeout: {timeout} seconds")
            self.flush_buffer()
            self.send_command("t", 1)
            data += self.retrieve_data(timeout=timeout)
            self.df = self.process_data(data)
        elif cmd_input == "p":
            if self.df is None:
                print("no data to print")
                return
            self.print_data(self.df)

        elif cmd_input == "t":
            self.send_command("t", 0)

        elif cmd_input == "c":
            self.send_command("r", 0)
            print(self.adc.read_until().decode())
        else:
            self.close_connection()
            exit(0)


def save_to_csv(buffer: list, filename: str):
    # write the data for this trace to dis

    with open(filename, "w") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(["cnt", "time_us", "acq_time", "data"])

        for string in buffer:
            row = string.split(",")
            writer.writerow(row)
    f.close()


def main(limit: int, suffix: str, t: str):
    logging.basicConfig(level=logging.DEBUG)
    finished = False
    capture_limit = limit
    ignored_data = ["", "/n", "/r"]
    buffer = ""
    recv = ""
    datalogger = DataLogger(timeout=0.1)

    # flush input buffer
    datalogger.adc.flushInput()
    # sleep(0.25)

    # send command to change capture limit
    datalogger.send_command("l", capture_limit)
    # print(f"capture_limit: {capture_limit}")
    # sleep(0.25)

    # send trigger
    datalogger.send_command("t", 0)
    print("triggered")
    # sleep(0.5)
    # recv = datalogger.adc.read_until().decode("utf-8")
    # print(f"recv: {recv}")

    # # check ready state
    # datalogger.send_command("r", 0)
    # sleep(1)
    # recv = datalogger.adc.read_until().decode("utf-8")
    # print(f"recv: {recv}")

    # read data from device
    start_time = time.process_time()
    while True:
        recv = datalogger.adc.read_until().decode()
        if ";" in recv:
            break
        buffer += recv

    save_to_csv(buffer.split("\r\n"), f"{capture_limit}_{t}us_{suffix}.csv")
    print(f"done, {time.process_time() - start_time}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(
        description="tests experiment execution and data logging"
    )

    parser.add_argument(
        "-limit", help="capture_limit", type=int, default=250,
    )

    parser.add_argument(
        "-t", help="time_us", type=str, default="250",
    )

    parser.add_argument(
        "-suffix", help="suffix", type=str, default="0",
    )

    args = parser.parse_args()

    main(**vars(args))
