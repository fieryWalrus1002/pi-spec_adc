import time
import os
from pathlib import Path
import glob


class TraceData:
    def __init__(self, buffer: str, note: str):
        self.buffer = buffer
        self.created = time.strftime("%y%m%d_%H%M%s")


class DataHandler:
    """Class to hold, export and import experiment data"""

    def __init__(self):
        self.trace_buffers = []

    def init_experiment(exp_name: str = "exp_name") -> bool:
        """Create directory for data export in format:
        /export/{today}_{exp_name}/
        
        params:
        exp_name: str
        """
        today = time.strftime("%y%m%d")
        if not os.path.exists(f"/export/{today}_{exp_name}"):
            os.makedirs(f"/export/{today}_{exp_name}")

    def parse_data():
        pass

    def save_buffer_to_csv(self, wl, trace_buffer, trace_num, trace_note):
        """give wavelength, str buffer of data, trace num, and note to save to csv"""
        trace_date = time.strftime("%d%m%y")
        trace_time = time.strftime("%H%M")

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

        # how many columns are there?
        data_col_count = len(trace_buffer.split("\n")[5]) - 2
        header_row = ["num", "time_us"] + ["val{i}" for i in range(data_col_count)]
        # write the data for this trace to disk
        with open(trace_filename, "w") as f:
            writer = csv.writer(f, delimiter=",")
            # writer.writerow(["trace_params", trace_params.parameter_string])
            writer.writerow(header_row)

            for row in trace_buffer.split("\n"):
                # print(row.split(","))
                writer.writerow(row.split(","))
        f.close()

        return trace_filename
