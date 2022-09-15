import logging
from io import StringIO
import argparse
import pandas as pd
from serial.serialutil import PARITY_NONE, STOPBITS_ONE
from dataclasses import dataclass


# from src.tracecontroller import TraceController, TraceControllerDebug
from datetime import datetime
import time


class TestClass:
    def __init__(self):
        self.status = "Yes."

    def test(self):
        return self.status


@dataclass
class TraceParams:
    num_points: int = 10000
    pulse_interval: int = 100
    meas_led_ir: int = 5
    meas_led_vis: int = 0
    pulse_length: int = 50
    sat_pulse_begin: int = 500
    sat_pulse_end: int = 600
    pulse_mode: int = 1
    trigger_delay: int = 0
    trace_note: str = "debug"
    act_intensity: tuple = (1, 2, 3)

    @property
    def param_string(self):
        return f"r{self.meas_led_ir};v{self.meas_led_vis};n{self.num_points};z{self.pulse_mode};i{self.pulse_interval};p{self.pulse_length};e{self.trigger_delay};w{self.act_intensity[0]};x{self.act_intensity[1]};y{self.act_intensity[2]};"


class PispecInterface:
    def __init__(self, tracecontroller):
        self.tracecontroller = tracecontroller
        self.data = []
        self.params = TraceParams()

    def get_data(self):
        return self.data

    def wait_for_response(self):
        recv = "hey"
        while ";" not in recv:
            recv = self.tracecontroller.receive_data()
        return recv

    def send_warning(self,):
        print("trigger in...")
        for i in range(0, 3):
            print(3 - i)
            time.sleep(1)

    

    def setup_trace(
        self, params: TraceParams(),
    ):
        """ setup the tracecontroller with provided trace parameters, and return
        the paramaters for verification"""
        self.params = params

        self.tracecontroller.set_parameters(params.param_string)

        return self.tracecontroller.get_parameters()

    def run_trace(self):
        
        trace_length_us = (self.params.num_points * (self.params.pulse_interval + self.params.pulse_length))
        print(f"trace_length_us: {trace_length_us}, in seconds: {trace_length_us * 1e-6}")
        # self.send_warning()
        # print("------------------------")\str_buffer = self.tracecontroller.receive_data(
        flushed = self.tracecontroller.flush_buffer()
        
        before_g = datetime.now()
      
        self.tracecontroller.set_parameters("m0")
        
        # wait for the trace to finish, or at least get near finishing
        sleep_time = trace_length_us * 1e-6 # convert usseconds to seconds
        time.sleep(sleep_time)

        print(f"trace_time: {sleep_time} s")
        # print(datetime.now().second)
        # time.sleep(sleep_time)
        # print(datetime.now().second)
        self.tracecontroller.set_parameters("g0")

        str_buffer = self.tracecontroller.get_trace_data()

        # str_buffer = self.tracecontroller.get_trace_data()

        after_g = (datetime.now() - before_g)

        print(f"trace_begun to data received: {after_g}")

        logging.debug("saving data")

        return str_buffer
        # if str_buffer != "":
        #     # we have a string buffer of our received data here
        #     csv_fn = self.tracecontroller.save_buffer_to_csv(
        #         wl=(str(self.params.meas_led_vis) + "_" + str(self.params.meas_led_ir)),
        #         trace_buffer=str_buffer,
        #         trace_num=0,
        #         trace_note="trace_note",
        #     )
        #     print(
        #         f"total time receiving and saving data was {(datetime.now().microsecond - before_g)/1000} ms"
        #     )
        #     print(f"saved data as {csv_fn}")
        #     return csv_fn

        # return pd.read_csv(csv_fn, delimiter=",")
        # else:
        #     return 1

        # return pd.DataFrame()


if __name__ == "__main__":
    pispec = PispecInterface()
    pispec.run_trace()
    print("done")
