import logging
from io import StringIO
import argparse
import os
from pickletools import int4
import pandas as pd
from serial.serialutil import PARITY_NONE, STOPBITS_ONE
from dataclasses import dataclass
from src.datahandler import DataHandler
from src.trace_utils import TraceParams
from tracecontroller import TraceController

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
        self.tracecontroller = TraceController(baud_rate=115200)
        self.datahandler = DataHandler()
        self.data = []
        self.params = TraceParams()

    def wait(self, time_s: int):
        time.sleep(time_s)

    def set_actinic(self, intensity: int):
        """set the current actinic intensit. not used during traces, but for in between
        traces and during pre-illumination

        params:
        intensity: desired intensity in uE
        """
        self.tracecontroller.modify_actinic(intensity=intensity)

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

        self.tracecontroller.set_parameters(params.param_string)

        return self.tracecontroller.get_parameters()

    def run_trace(self, rep: int = 0, note: str = "", timeout: int = 1000000) -> int:

        trace_length_us = self.params.num_points * (
            self.params.pulse_interval + self.params.pulse_length
        )

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
        return self.datahandler.get_dataframe()

    def power(self, power_state: bool):
        if power_state:
            return self.tracecontroller.switch_pulser_power(1)
        else:
            return self.tracecontroller.switch_pulser_power(0)
