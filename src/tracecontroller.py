from numpy import byte
import serial
import serial.tools.list_ports
import logging
import time
from sys import platform
from pathlib import Path
import csv


class TraceController:
    def __init__(self, baud_rate: int = 115200, timeout: float = 1.0):
        self.ser = None
        self.connect_ser(baud_rate, timeout)
        self.data = []
        logging.debug("and now we're done with init")

    def connect_ser(self, baud_rate, timeout):
        """connects to microcontroller device with serial, returns connection to device
        3-21-22 now using Teensy 4.1
        idVendor=16c0, idProduct=0483, bcdDevice= 2.80
        Product: USB Serial
        Manufacturer: Teensyduino
        SerialNumber: 10167240
                
        Was a chipkit MX3 from Digilent @ ttyUSB0, displays as:
        FT232R USB UART - FT232R USB UART ttyUSB0 /dev/ttyUSB0 1027 24577
        """

        for port in serial.tools.list_ports.comports():

            if port.vid == int("16c0", 16):
                print(port.vid)
                device = port.device
                logging.debug(device)

        while self.ser is None:
            logging.debug(f"connection to {device} initiated.")
            self.ser = serial.Serial(device, baud_rate, timeout=timeout)

            if self.ser is None:
                time.sleep(1)

        logging.debug(f"ser connected at {device}")
        logging.debug("so we're done with connect_sr")

    def get_diagnostic_info(self):
        return self.ser

    def get_num_points(self):
        self.set_parameters("d")
        time.sleep(0.25)
        recv = self.ser.readline()
        return recv

    def get_parameters(self):
        self.set_parameters("d0")
        time.sleep(0.25)
        params = self.receive_data(timeout=0.001)
        return params

    def set_parameters(self, cmd_input="", value=0):
        cmd_output = cmd_input + str(value) + ";"
        self.ser.write(cmd_output.encode("utf-8"))

    def read_buffer(self):
        recv = self.ser.readline()
        return recv

    def receive_data(self) -> list:
        """waits for data to be received from the ADC, then returns it as a list"""
        strbuf = ""

        while self.ser.in_waiting > 0:
            recv = self.ser.read_until()

        return strbuf

    def decode_data(self, buffer):
        strbuf = ""
        for i in buffer:
            strbuf += i.decode()
        return strbuf

    def get_trace_data(self, num_points):
        # // returns string buffer of received bytes
        buffer = ""
        recv_timepoint = 0
        timeout_cnt = 0
        recv = bytearray()
        recv_state = True

        while recv_state:
            if self.ser.in_waiting > 0:
                recv.extend(self.ser.read_all())
                try:
                    decoded = recv.decode()
                except UnicodeDecodeError:
                    logging.debug("unicode error")

                if len(decoded) > 96:
                    buffer += decoded
                    timeout_cnt = 0
                    recv = bytearray()

            timeout_cnt += 1

            if timeout_cnt > 10000:
                logging.debug("timed out")
                return buffer

        return buffer

    def save_buffer_to_csv(self, wl, trace_buffer, trace_num, trace_note):
        """ give wavelength, str buffer of data, trace num, and note to save to csv """
        trace_date = time.strftime("%d%m%y")
        trace_time = time.strftime("%H%M")

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
        with open(trace_filename, "w") as f:
            writer = csv.writer(f, delimiter=",")
            # writer.writerow(["trace_params", trace_params.parameter_string])
            writer.writerow(["num", "time_us", "value"])

            for row in trace_buffer.split("\n"):
                # print(row.split(","))
                writer.writerow(row.split(","))
        f.close()
        logging.debug(trace_filename)

        return trace_filename

