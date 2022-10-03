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
        self.params = TraceParams()
        self.tracecontroller = TraceController()
        self.datahandler = DataHandler()
        self._max_intensity = 255

    def wait(self, time_s: int):
        time.sleep(time_s)

    def _check_tc_connection(self):
        while self.tracecontroller.connected() == False:
            self.tracecontroller.connect_to_device()
            print("tc disconnected, reconnecting...")

    def set_actinic_intensity(self, intensity: int):
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
            return f"Error: accepts only integer values 0-255, you input was {type(intensity)}"

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
            print(f"dest_path does not exist, creating {dest_path}")
            os.makedirs(dest_path)
        else:
            print(f"dest_path exists: {dest_path}")

        self.datahandler = DataHandler()
        print("DataHandler created for these traces")

        self.set_power_state(1)
        print("setting power state")

        return dest_path

    def conclude_experiment(self):
        self.set_power_state(0)
        return f"Experiment concluded, trace data is ready for processing."

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

    def run_trace(self, rep: int = 0, note: str = "", timeout_s: float = 1.0) -> int:

        trace_length_us = self.params.num_points * (
            self.params.pulse_interval + self.params.pulse_length
        )

        self._check_tc_connection()

        self.tracecontroller.flush_buffer()

        trace_begun = time.time()

        self.tracecontroller.set_parameters("m0")

        sleep_time = trace_length_us * 1e-6
        time.sleep(sleep_time)  # sleep until trace is done
        status, str_buffer = self.tracecontroller.get_trace_data(timeout_s=timeout_s)
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

    def get_dataframe_list(self):
        """retrieves list of dataframes from data handler module"""
        dfs = self.datahandler.get_dataframe_list()

        # return [self.process_dataframe(df) for df in dfs]
        return [df for df in dfs]

    def _get_nm(self, param_string: str):
        # import re

        # resp = re.findall(pattern="v[0-9]", string=df.param_string[0])
        # print(resp)
        return 0

    def process_dataframe(self, df):
        """takes the raw dataframe and calculates a few neccessary variables before
        returning it
        """

        # dA = (- deltaT/T)/2.3

        df["nm"] = self._get_nm(df["param_string"])

        # row means of all the data points
        df["val"] = df[["aq_0", "aq_1", "aq_2", "aq_3", "aq_4"]].mean(
            numeric_only=True, axis=1
        )
        df["zero_val"] = df[["paq_0", "paq_1", "paq_2"]].mean(numeric_only=True, axis=1)
        df["V"] = (df["val"] - df["zero_val"]) * (12 / 65535)
        df["time_ms"] = df["time_us"] / 1000

        # prepulse_mean = df.iloc[350:400, -1].mean()
        prepulse_mean = 1
        df["dAbs"] = -(df["V"] / prepulse_mean) / 2.3

        df.set_index("time_us", inplace=True)

        return df

    def actinic_test(self):

        test = [x * 20 for x in range(4, 7)]

        self.set_power_state(1)

        for intensity in test:

            self.set_actinic_intensity(intensity)
            # pispec.set_power_state(1)
            self.set_actinic_state(1)

            self.wait(1)

            self.set_actinic_state(0)
            self.set_actinic_intensity(0)
            # pispec.set_power_state(0)

            self.wait(1)

        self.set_power_state(0)

    def set_actinic_state(self, switch_state: int) -> str:
        """turn on and off the transistor gate controlling the variable output voltage
        to actinic circuit"""

        output = 0 if switch_state <= 0 else 1

        self.tracecontroller.set_parameters(f"u{output}")

        return output

    def set_power_state(self, switch_state: int) -> str:
        """Turn on the power to the LEDs. If this is off, the LEDs will not have 12V
        power and will not turn on.

        Power state should be turned off when experiments are done, to prevent LED
        burnout accidents.

        switch_state: int. 0 to turn off the power switch, 1 to turn it on.
        """
        output = 0 if switch_state <= 0 else 1

        # self.tracecontroller.set_parameters(f"k{output}")

        return output

    def meas_led_test(
        self,
        pins: list = [2, 3, 4, 5, 6, 7, 8, 9],
        pulse_length: int = 75,
        pulse_interval: int = 1000,
    ):
        """runs a pin pulse test for the list of given pin numbers. Repeats num_points times,
        pulse is pulse_length us wide and interval is pulse_interval."""

        self.set_power_state(1)

        self.tracecontroller.set_parameters(f"i{pulse_interval};p{pulse_length}")

        for pin in pins:
            self.tracecontroller.set_parameters(f"c{pin}")
            self.wait(2)

        self.set_power_state(0)
