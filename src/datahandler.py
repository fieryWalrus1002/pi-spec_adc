import csv
import time
from pathlib import Path
from src.trace_utils import TraceData
import pandas as pd
from io import StringIO
import re
import numpy as np


class DataHandler:
    """Class to hold, export and import experiment data"""

    def __init__(self):
        self.trace_buffers = []
        self.created = time.time()
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

    def clear_buffer(self):
        self.trace_buffers = []

    def save_buffer(
        self,
        buffer: str,
        note: str,
        param_string: str,
        trace_begun: float,
        trace_end: float,
        rep: int,
    ):
        """ " takes a decoded string buffer and appends it to a TraceData list"""
        self.trace_buffers.append(
            TraceData(
                rep=rep,
                buffer=buffer,
                trace_num=len(self.trace_buffers),
                trace_begun=trace_begun,
                trace_end=trace_end,
                param_string=param_string,
                note=note,
            )
        )

    def calc_d_abs(self, df):
        """calculates delta A, or delta absorbance
        deltaT = the change in transmission over the course of the trace in voltage terms
        T = mean pre-pulse transmission. use the last 200 pts or so before the saturation pulse.

        d_abs = -(deltaT/T)/2.3
        """
        sat_pulse_begin = int(
            re.search("s[0-9]{1,4}", df.loc[0, "param_string"]).group()[1:]
        )
        sat_pulse_end = int(
            re.search("t[0-9]{1,4}", df.loc[0, "param_string"]).group()[1:]
        )
        num_points = int(
            re.search("n[0-9]{1,4}", df.loc[0, "param_string"]).group()[1:]
        )
        prepulse_mean = np.mean(
            df.loc[sat_pulse_begin - 200 : sat_pulse_begin - 1, "V"]
        )

        return -(df["V"] / prepulse_mean) / 2.3

    def get_meas_vis_num(self, df):
        return int(re.search("v[0-9]{1,2}", df.loc[5, "param_string"]).group()[1:])

    def get_meas_ir_num(self, df):
        return int(re.search("r[0-9]{1,2}", df.loc[5, "param_string"]).group()[1:])

    def process_df(self, df):
        # self.correct_v_shift(df)
        df["val"] = df[["aq_0", "aq_1", "aq_2", "aq_3", "aq_4"]].mean(
            numeric_only=True, axis=1
        )
        df["zero_val"] = df[["paq_0", "paq_1", "paq_2"]].mean(numeric_only=True, axis=1)
        df["raw_diff"] = df["val"] - df["zero_val"]
        df["V"] = df["raw_diff"] * (12 / 65535)
        df["time_ms"] = df["time_us"] / 1000
        df["nm"] = self.nm_strs[self.get_meas_vis_num(df)]
        df["d_abs"] = self.calc_d_abs(df)

        return df

    def correct_v_shift(self, df):
        sat_pulse_begin = int(
            re.search("s[0-9]{1,4}", df.loc[0, "param_string"]).group()[1:]
        )
        sat_pulse_end = int(
            re.search("t[0-9]{1,4}", df.loc[0, "param_string"]).group()[1:]
        )
        print(f"begin, end: {sat_pulse_begin},{sat_pulse_end}")
        phase0 = np.mean(
            df.loc[0:sat_pulse_begin, ["paq_0", "paq_1", "paq_2"]].mean(
                numeric_only=True, axis=1
            )
        )
        phase1 = np.mean(
            df.loc[sat_pulse_begin:sat_pulse_end, ["paq_0", "paq_1", "paq_2"]].mean(
                numeric_only=True, axis=1
            )
        )
        phase2 = np.mean(
            df.loc[sat_pulse_end:, ["paq_0", "paq_1", "paq_2"]].mean(
                numeric_only=True, axis=1
            )
        )
        print(
            f"phase differences {phase0 - phase0},{phase1 - phase0},{phase2 - phase0}"
        )
        df.loc[
            sat_pulse_end:,
            ["paq_0", "paq_1", "paq_2", "aq_0", "aq_1", "aq_2", "aq_3", "aq_4"],
        ] = df.loc[
            sat_pulse_end:,
            ["paq_0", "paq_1", "paq_2", "aq_0", "aq_1", "aq_2", "aq_3", "aq_4"],
        ] - (
            phase2 - phase0
        )

        return df

    def parse_tdata(
        self,
        tdata: TraceData,
    ) -> pd.DataFrame:
        """
        takes a tracedata string buffer of data from the tracecontroller and converts it to a
        dataframe, and adds the metadata for each point

        data coming in from the buffer will look like:
        0,0, 0, 0, 0, 9728, 9984, 9984, 9984, 9984, 9984\\r\\n
        1,501, 0, 0, 0, 9728, 9984, 9984, 9984, 9984, 9984\\r\\n

        """

        f = StringIO(tdata.buffer)

        df = pd.read_csv(f, header=None, names=tdata.col_names[0])

        metadf = pd.DataFrame(tdata.asdict(), index=[i for i in range(0, df.shape[0])])

        df = pd.concat([metadf, df], axis=1)

        return df
        # get trace data columns set up and join to dataframe

    def get_df(self):
        """get processed experiment dataframe"""

        dfs = [
            self.process_df(self.parse_tdata(tdata=tdata))
            for tdata in self.trace_buffers
        ]

        col_names = dfs[0].columns
        df = pd.DataFrame(columns=col_names)

        for d in dfs:
            df = pd.concat((df, d))

        return df
