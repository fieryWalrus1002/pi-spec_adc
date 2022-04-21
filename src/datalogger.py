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

class DataLogger:
    def __init__(self):
        self.packet_size = 1000 
        self.data = []
        self.df = None

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

            for row in data:
                writer.writerow(row.split(","))
        f.close()

        return trace_filename
