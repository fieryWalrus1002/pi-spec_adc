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

    def _send_command(self, cmd_input, value):
        cmd_output = cmd_input + str(value) + ";"
        self.adc.write(cmd_output.encode("utf-8"))

    def receive_data(timeout: float) -> list:
        """ waits for data to be received from the ADC, then returns it as a list """        
        data = []               
        buffer = ""
        recv = ""
        
        # read data from device
        start_time = time.process_time()
        while not _timedout(timeout=timeout, start_time=start_time):
            recv = datalogger.adc.read_until().decode()
            if ";" in recv:
                break
            buffer += recv

        data = buffer.split("\r\n")
        
        return data

    def ready_scan(self, num_points):
        """ updates ADC on how many data points to expect, and then triggers measurement
        mode.
        Parameters
        num_points: the number of incoming triggers that the ADC will expect. 
        """
        # flush input buffer
        self.datalogger.adc.flushInput()

        # send command to change capture limit
        self.datalogger._send_command("l", num_points)   
        logging.debug(f"capture_limit updated to {num_points}")

        # send trigger
        self.datalogger._send_command("t", 0)
        logging.debug("triggered")
    
    # def save_to_csv(self, buffer: list, filename: str):
    #     # write the data for this trace to dis

    #     with open(filename, "w") as f:
    #         writer = csv.writer(f, delimiter=",")
    #         writer.writerow(["cnt", "time_us", "acq_time", "data"])

    #         for string in buffer:
    #             row = string.split(",")
    #             writer.writerow(row)
    #     f.close()

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
            writer.writerow(["num", "time_us", "acq_time", "value"])

            for row in trace_data:
                writer.writerow(row.split(","))
        f.close()

        return trace_filename


    def _timedout(self, start_time: float, timeout: float = 1.0) -> bool:
        """ checks to see if the while loop should timeout. Returns true if timeout is reached """
        # logging.debug(f"start_time: {start_time}, now: {time.process_time()}")
        return ((time.process_time() - start_time) >= timeout)


# def main(limit: int, suffix: str, rec_timeout: str):
#     logging.basicConfig(level=logging.DEBUG)
    
#     capture_limit = limit
#     ignored_data = ["", "/n", "/r"]
#     buffer = ""
#     recv = ""
#     datalogger = DataLogger(0.1)

#     # flush input buffer
#     datalogger.adc.flushInput()
#     # sleep(0.25)

#     # send command to change capture limit
#     datalogger._send_command("l", capture_limit)
#     # print(f"capture_limit: {capture_limit}")
#     # sleep(0.25)

#     # send trigger
#     datalogger._send_command("t", 0)
#     logging.debug("triggered")
#     # sleep(0.5)
#     # recv = datalogger.adc.read_until().decode("utf-8")
#     # print(f"recv: {recv}")

#     # # check ready state
#     # datalogger._send_command("r", 0)
#     # sleep(1)
#     # recv = datalogger.adc.read_until().decode("utf-8")
#     # print(f"recv: {recv}")

#     # read data from device
#     start_time = time.process_time()
#     while not timedout(timeout=rec_timeout, start_time=start_time):
#         recv = datalogger.adc.read_until().decode()
#         if ";" in recv:
#             break
#         buffer += recv

#     save_to_csv(buffer.split("\r\n"), f"{capture_limit}_{suffix}.csv")
#     logging.debug(f"{end_status(buffer, capture_limit)}, time:{time.process_time() - start_time}")

# if __name__ == "__main__":
#     logging.basicConfig(level=logging.DEBUG)

#     parser = argparse.ArgumentParser(
#         description="tests experiment execution and data logging"
#     )

#     parser.add_argument(
#         "-limit", help="capture_limit", type=int, default=250,
#     )

#     parser.add_argument(
#         "-rec_timeout", help="timeout value for serial data recovery", type=float, default=5,
#     )

#     parser.add_argument(
#         "-suffix", help="suffix", type=str, default="0",
#     )



#     args = parser.parse_args()

#     main(**vars(args))