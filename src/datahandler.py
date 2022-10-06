import csv
import time
from pathlib import Path
from src.trace_utils import TraceData
import pandas as pd
from io import StringIO
import re


class DataHandler:
    """Class to hold, export and import experiment data"""

    def __init__(self):
        self.trace_buffers = []
        self.created = time.time()

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

    def get_dataframe_list(self):
        """returns a list of dataframes converted from trace buffers"""

        dfs = [self.parse_tdata(tdata=tdata) for tdata in self.trace_buffers]

        return dfs

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
