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
from src.drive import DataUploader
import matplotlib.pyplot as plt

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
        self.config = None
        self.params = TraceParams()
        self.tracecontroller = TraceController()
        self.datahandler = DataHandler()
        self._max_intensity = 255
        self.wavelength_dict = {
            "none": 0,
            "520": 1,
            "545": 2,
            "554": 3,
            "563": 4,
            "572": 5,
            "830": 6,
            "940": 7,
        }
        self.nm_strs = [i for i in self.wavelength_dict]
        # self.img_export_path = "img_export"
        self.dest_path = 'export'

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

        self.dest_path =f"{os.getcwd()}/export/{today}_{exp_name}"

        if not os.path.exists(self.dest_path):
            os.makedirs(self.dest_path)

        print(f"os.path.exists: {self.dest_path}, {os.path.exists(self.dest_path)}")
        self.datahandler = DataHandler()
        self.datahandler.clear_buffer()

        self.set_power_state(1)

        return self.dest_path

    def conclude_experiment(self):
        self.set_power_state(0)
        return f"Experiment concluded, trace data is ready for processing."

    def setup_trace(
        self,
        params: TraceParams(),
    ):
        """ set self.params to the given parameters, and then send the parameter string to the trace controller """
        self.params = params
        self.tracecontroller.set_parameters(self.params.param_string)
        return self.tracecontroller.get_parameters()

    def run_trace(self, rep: int = 0, note: str = "", timeout_s: float = 1.0) -> int:

        trace_length_us = self.params.num_points * (
            self.params.pulse_interval + self.params.pulse_length
        )

        trace_begun = time.time()

        self.tracecontroller.set_parameters("m0")

        time.sleep(trace_length_us / 1000000 * 1.5)

        trace_end = time.time()

        exit_code, str_buffer = self.tracecontroller.get_trace_data(timeout_s=timeout_s)

        self.datahandler.save_buffer(
            rep=rep,
            buffer=str_buffer,
            note=note,
            param_string=self.params.param_string,
            trace_begun=trace_begun,
            trace_end=trace_end,
        )
        return exit_code

    # def process_dataframe(self, df):
    #     """takes the raw dataframe and calculates a few neccessary variables before
    #     returning it
    #     """

    #     # dA = (- deltaT/T)/2.3

    #     df["nm"] = self._get_nm(df["param_string"])

    #     # row means of all the data points
    #     df["val"] = df[["aq_0", "aq_1", "aq_2", "aq_3", "aq_4"]].mean(
    #         numeric_only=True, axis=1
    #     )
    #     df["zero_val"] = df[["paq_0", "paq_1", "paq_2"]].mean(numeric_only=True, axis=1)
    #     df["V"] = (df["val"] - df["zero_val"]) * (12 / 65535)
    #     df["time_ms"] = df["time_us"] / 1000

    #     # prepulse_mean = df.iloc[350:400, -1].mean()
    #     prepulse_mean = 1
    #     df["dAbs"] = -(df["V"] / prepulse_mean) / 2.3

    #     df.set_index("time_us", inplace=True)

    #     return df

    def actinic_test(self, delay: int = 1, int_values: list = range(0, 255, 10)):

        self.set_power_state(1)

        for intensity in int_values:

            self.set_actinic_intensity(intensity)
            # pispec.set_power_state(1)
            self.set_actinic_state(1)

            self.wait(delay)

            self.set_actinic_state(0)
            self.set_actinic_intensity(0)

            self.wait(delay / 3)

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

    def get_meas_led_numbers(self, nm_str_list: list[str]):
        return [self.wavelength_dict[x] for x in nm_str_list]

    def run_experiment(
        self,
        exp_name: str = "test",
        wavelengths: list = ["520"],
        act_phase_vals: list = [0, 200, 0],
        btwn_trace_delay: int = 2
    ):
        """This function runs a basic experiment, with each wavelength listed in the
        wavelengths list run once."""

        print(f"running experiment with the following wavelengths: {wavelengths}")
        nm_wl = self.get_meas_led_numbers(wavelengths)
        trace_params = [
            TraceParams(
                num_points=1000,
                pulse_interval=1000,
                meas_led_ir=0,
                meas_led_vis=x,
                pulse_length=85,
                sat_pulse_begin=400,
                sat_pulse_end=600,
                pulse_mode=1,
                trigger_delay=45,
                trace_note=exp_name,
                act_intensity=act_phase_vals,
            )
            for x in nm_wl
        ]

        dest_path = self.init_experiment(exp_name=exp_name)
        print(f"runtrace says dest path is : {dest_path}")
        for param in trace_params:
            device_params = self.setup_trace(param)
            print(device_params)
            self.wait(btwn_trace_delay)
            self.run_trace(timeout_s=2.5)

        self.conclude_experiment()

    def save_df(self, df: pd.DataFrame, filepath: str = None):
        dest_path = filepath if filepath != None else self.dest_path
        print(f'saving to {self.dest_path}')
        return self.datahandler.save_df(df, dest_path)


    def get_df(self):
        return self.datahandler.get_df()

    def plot_df(self, df, nm, col, upload: bool == False):
        """ helper function to create a plot and save it to disk/ upload to gdrive """
        filename = f'{self.dest_path}/{datetime.now().strftime("%y%m%d_%H%M")}_{nm}nm_{col}.png'
        subdf = df.loc[df['nm'] == nm]
        subdf.plot(x='time_ms',y=col,kind='scatter',
                    c='cornflowerblue',
                    title=f"{nm}nm {col} vs time_ms",
                    ylabel=f"{col}",
                    xlabel="time (ms)",
                    s=10)

        plt.savefig(filename)

        if upload:
            self.datahandler.upload(filename)