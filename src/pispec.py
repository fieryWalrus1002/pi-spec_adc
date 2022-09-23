import logging
from io import StringIO
import argparse
import serial
import os
from pickletools import int4
import pandas as pd
from serial.serialutil import PARITY_NONE, STOPBITS_ONE
from dataclasses import dataclass
from src.datahandler import DataHandler
from src.trace_utils import TraceParams
from src.tracecontroller import TraceController

# from src.tracecontroller import TraceController, TraceControllerDebug
from datetime import datetime
import time


class TestClass:
    def __init__(self):
        self.status = "Yes."

    def test(self):
        return self.status


class PiSpec:
    def __init__(self):
        self.tracecontroller = TraceController()
        self.datahandler = DataHandler()
        self.params = TraceParams()
        self._max_intensity = 255

    def wait(self, time_s: int):
        time.sleep(time_s)

    def _check_tc_connection(self):
        while self.tracecontroller.connected() == False:
            self.tracecontroller.connect_to_device()
            print("tc disconnected, reconnecting...")

    def set_actinic(self, intensity: int):
        """set the current actinic intensit. not used during traces, but for in between
        traces and during pre-illumination

        params:
        intensity: 0-255 range of intensity, not currenbtly correlated to uE
        """
        if intensity >= 0 and intensity <= 255 and type(intensity) == int:
            cmd = str(f"a{intensity}")
            resp = self.tracecontroller.set_parameters(cmd)
            # print(f"set_actinic: {cmd}, resp: {resp}")
            return resp
        else:
            return  f"Error: accepts only integer values 0-255, you input was {type(intensity)}"

        # print(cmd, ", ", cmd_sent)

        # self._check_tc_connection()

        # if intensity > self._max_intensity:
        #     self.tracecontroller.modify_actinic(intensity=self._max_intensity)
        # else:

    def init_experiment(self, exp_name: str) -> bool:
        """Create directory for data export in format:
        /export/{today}_{exp_name}/

        params:
        exp_name: str
        """
        today = time.strftime("%y%m%d")
        dest_path = f"{os.getcwd()}/export/{today}_{exp_name}"
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)
        self.datahandler = DataHandler()

    def setup_trace(
        self,
        params: TraceParams(),
    ):
        """setup the tracecontroller with provided trace parameters, and return
        the paramaters for verification"""
        self.params = params

        self._check_tc_connection()

        self.tracecontroller.set_parameters(params.param_string)

        return self.tracecontroller.get_parameters()

    def run_trace(self, rep: int = 0, note: str = "", timeout: int = 1000000) -> int:

        trace_length_us = self.params.num_points * (
            self.params.pulse_interval + self.params.pulse_length
        )

        self._check_tc_connection()

        self.tracecontroller.flush_buffer()

        trace_begun = time.time()

        self.tracecontroller.set_parameters("m0")

        sleep_time = trace_length_us * 1e-6
        time.sleep(sleep_time)  # sleep until trace is done

        status, str_buffer = self.tracecontroller.get_trace_data(timeout=timeout)

        trace_end = time.time()

        self.datahandler.save_buffer(
            rep=rep,
            buffer=str_buffer,
            note=note,
            param_string=self.params.param_string,
            trace_begun=trace_begun,
            trace_end=trace_end,
        )

        return status

    def get_data(self):
        self._check_tc_connection()

        return self.datahandler.get_dataframe()

    def power(self, switch_state) -> str:
        """1/0, True/False, or "on"/"off" all work to change the LED power state"""

        on_statements = (True, 1, "on", "ON")

        output = 1 if switch_state in on_statements else 0

        self._check_tc_connection()

        self.tracecontroller.switch_pulser_power(output)

        return output
