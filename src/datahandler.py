import csv
import os
import time
from pathlib import Path
from src.trace_utils import TraceData
import pandas as pd
from io import StringIO
import re
import numpy as np
from src.drive import DataUploader
from datetime import datetime


class DataHandler:
    """Class to hold, export and import experiment data"""

    def __init__(self):
        self.trace_buffers = []
        self.created = time.time()
        self.nm_str_dict = {
            "0": 0,
            "520": 1,
            "545": 2,
            "554": 3,
            "563": 4,
            "572": 5,
            "830": 6,
            "940": 7,
        }
        self.nm_num_dict = {value: key for key, value in self.nm_str_dict.items()}
        self.uploader = DataUploader()
        self.debug_list = []

    def clear_buffer(self):
        self.trace_buffers = []

    def _column_names_from_buffer(self, buffer: str) -> list:
        """gets the appropriate columnns names from buffer"""
        num_variables = len(buffer.split("\r\n")[0].split(",")) - 2
        # #print(f"num_variables: {num_variables}")

        column_names = (
            ["pt_num", "time_us"]
            + [f"z_{i}" for i in range(0, num_variables // 3)]
            + [f"p_{i}" for i in range(0, num_variables - (num_variables // 3))]
        )

        # #print(f"in _column_names_from_buffer: {type(column_names)}")
        # #print("returning ", column_names, "length ", len(column_names))

        return column_names

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
        trace_index = len(self.trace_buffers)

        new_trace_data = TraceData(
            rep=rep,
            buffer=buffer,
            trace_num=trace_index,
            trace_begun=trace_begun,
            trace_end=trace_end,
            param_string=param_string,
            note=note,
        )

        self.trace_buffers.append(new_trace_data)

    def save_df(self, df, filepath, upload: bool = False) -> str:

        exp_name = "_".join(filepath.split("/")[-1].split("_")[1:])

        filename = (
            f'{filepath}/{datetime.now().strftime("%y%m%d_%H%M")}_{exp_name}.csv'
        )
        df.to_csv(filename)

        if upload:
            self.upload(f"{filename}")
        return filename

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
        nm = re.search("v[0-9]{1,2}", df.loc[5, "param_string"]).group()[1:]
        return int(nm)

    def get_meas_ir_num(self, df):
        return int(re.search("r[0-9]{1,2}", df.loc[5, "param_string"]).group()[1:])

    def param_from_string(self, param: str, param_string: str) -> int:
        pattern = rf"(?<={param}=)[0-9]+"
        return int(re.search(pattern, param_string).group())

    def aq_nums(self, param_string: str) -> list:
        """returns two lists of the pre acquisition and acquisition labels for columns in the dataset"""
        return [
            f"paq_{i}"
            for i in range(0, self.param_from_string("numPreAq", param_string))
        ], [f"aq_{i}" for i in range(0, self.param_from_string("numAq", param_string))]

    def get_df(self):
        """return a processed dataframe"""

        return pd.concat([self.process_df(tdata) for tdata in self.trace_buffers])

    def process_df(self, tdata):
        df = self.parse_tdata(tdata=tdata)
        new_names = [name for name in df.columns[0:7]]

        df.columns = new_names + self._column_names_from_buffer(tdata.buffer)
        #print("renamed ", df.columns)

        if df["param_string"][0] == None:
            return None


        # paq_num, aq_num = self.aq_nums(df["param_string"][0])
        # #print(paq_num, aq_num)
        # df["val"] = df[aq_num].mean(numeric_only=True, axis=1)
        # df["zero_val"] = df[paq_num].mean(numeric_only=True, axis=1)
        # df["raw_diff"] = df["val"] - df["zero_val"]
        # df["V"] = df["raw_diff"] * (12 / 65535)
        df["time_ms"] = df["time_us"] / 1000
        df["nm"] = self.nm_num_dict[self.get_meas_vis_num(df)]
        # df["d_abs"] = self.calc_d_abs(df)

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

        df = pd.read_csv(f, header=None)

        metadf = pd.DataFrame(tdata.asdict(), index=[i for i in range(0, df.shape[0])])

        df = pd.concat([metadf, df], axis=1)

        return df

    def upload(self, file):
        self.uploader.upload(file)


if __name__ == "__main__":
    dh = DataHandler()
