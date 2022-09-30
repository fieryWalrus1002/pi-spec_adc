import csv
import time
from pathlib import Path
from src.trace_utils import TraceData
import pandas as pd
from io import StringIO


class DataHandler:
    """Class to hold, export and import experiment data"""

    def __init__(self):
        self.trace_buffers = []
        self.created = time.time()

    def save_buffer(
        self,
        buffer: str,
        note: str,
        param_string: str,
        trace_begun: float,
        trace_end: float,
        rep: int,
    ):
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

    def convert_tdata_to_df(self, tdata: TraceData) -> pd.DataFrame:

        df = self.parse_buffer(tdata=tdata)

        return df

    def parse_buffer(self, tdata: TraceData) -> pd.DataFrame:
        """
        takes a tracedata string buffer of data from the tracecontroller and converts it to a
        dataframe, and adds the metadata for each point
        """
        data_list = []
        meta_cols, meta_vals = tdata.metadata
        buffer = tdata.buffer.split("\r\n")

        i = 0
        j = 0
        buf_len = len(buffer)
        first_line = len(buffer)
        last_line = 0

        for i in range(0, buf_len):
            len1 = len(buffer[i].split(","))
            len2 = len(buffer[i + 1].split(","))
            
            if len1 == len2:
                first_line = i
                break           

        for i in range(0, buf_len):
            len1 = len(buffer[buf_len - i - 1].split(","))
            len2 = len(buffer[buf_len - i - 2].split(","))
            
            if len1 == len2:
                last_line = i - 1
                break          
        
        
        
        for i, line in enumerate(buffer[first_line:last_line]):

            
            spl_line = line.split(",")               

            for i, item in enumerate(spl_line):
                try: 
                    spl_line[i] = float(item)
                except:
                    #mwahahahahahah
                    pass

            if len(spl_line) > 1:
                data_list.append(meta_vals + spl_line)

            
               
        num_cols = len(buffer[first_line].split(","))
        
        aq_cols = [f"aq_{x}" for x in range(0, num_cols - 2)]
        
        columns = meta_cols + ["pt_num", "time_us"] + aq_cols
        
        df = pd.DataFrame(data_list, columns=columns)
        

        return df

    def get_dataframe(self):
    
        dfs = [self.convert_tdata_to_df(tdata) for tdata in self.trace_buffers]

        return dfs
    
    

