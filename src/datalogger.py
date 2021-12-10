import argparse
import csv
import io
import logging
import math
import random
import time
from itertools import count

from datetime import datetime
from pathlib import Path
from sys import exit
from time import sleep
from multiprocessing import Process
import pandas as pd
import serial
import serial.tools.list_ports

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

    def receive_data(self, timeout: float) -> list:
        """ waits for data to be received from the ADC, then returns it as a list """        
        data = []               
        buffer = ""
        recv = ""
        
        # read data from device
        start_time = time.process_time()
        while not self._timedout(timeout=timeout, start_time=start_time):
            recv = self.adc.read_until().decode()
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
        self.adc.flushInput()

        # send command to change capture limit
        self._send_command("l", num_points)   
        logging.debug(f"capture_limit updated to {num_points}")

        # send trigger
        self._send_command("t", 0)
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
