import serial
import serial.tools.list_ports
import logging
import time
from threading import Thread

param_dict: dict = {
    "write_act_intensity": "a",
    "get_params": "d",
    "trigger_delay": "e",
    "push_data": "g",
    "pulse_interval": "i",
    "detector_circuit": "j",
    "power_12v": "k",
    "execute_trace": "m",
    "num_points": "n",
    "pulse_length": "p",
    "meas_led_ir": "r",
    "sat_pulse_end": "s",
    "sat_pulse_begin": "t",
    "act_gate": "u",
    "meas_led_vis": "v",
    "act_phase_0": "w",
    "act_phase_1": "x",
    "act_phase_2": "y",
    "pulse_mode": "z",
}


class TraceController:
    def __init__(
        self, baud_rate: int = 115200, timeout_s: float = 1.0, params: str = "d0"
    ):
        self.baud_rate = baud_rate
        self.timeout_s = timeout_s
        self.device = self.get_device_port()
        self.ser = self.connect_to_device()
        self.data = []
        self.daemon = Thread(daemon=True, target=self.check_conn_status)
        self.daemon.start()
        self.max_intensity = 255  # limit on how high you can set the actinic, in 0-255
        # self.set_parameters(params)

    def _debug(self):
        return self.set_parameters("o0")

    def check_conn_status(self, interval_sec: float = 0.25):
        while True:
            if self.connected == False:
                self.ser = self.connect_to_device()
            time.sleep(interval_sec)

    def connect_to_device(self):
        ser = None
        start_time = time.time()

        while ser is None:
            ser = serial.Serial(
                port=self.device,
                baudrate=self.baud_rate,
                timeout=self.timeout_s,
                write_timeout=self.timeout_s,
            )
            time.sleep(0.5)
            print(f"waiting for serial... {(time.time() - start_time)/1000}")

        # print(f"connect_to_device() connecting to {self.device}")
        return ser

    def connected(self):
        try:
            resp = self.ser.isOpen()
        except serial.SerialException as e:
            print(f"error: {e}")
            return False
        return resp

    def flush_buffer(self) -> bool:
        self.ser.flush()
        return True

    def switch_pulser_power(self, power: bool, timeout: int) -> str:

        if power:
            self.set_parameters("q1")
        else:
            self.set_parameters("q0")

        return self.read_ser_buffer(timeout=timeout)

    def get_device_port(self):
        """connects to microcontroller device with serial, returns connection to device
        3-21-22 now using Teensy 4.1
        idVendor=16c0, idProduct=0483, bcdDevice= 2.80
        Product: USB Serial
        Manufacturer: Teensyduino
        SerialNumber: 10167240

        Was a chipkit MX3 from Digilent @ ttyUSB0, displays as:
        FT232R USB UART - FT232R USB UART ttyUSB0 /dev/ttyUSB0 1027 24577
        """

        for port in serial.tools.list_ports.comports():
            if port.vid == int("16c0", 16):
                device = port.device
                logging.debug(device)
        return device

    def get_diagnostic_info(self):
        return self.ser

    def get_num_points(self):
        self.set_parameters("d0")
        return self.read_ser_buffer()

    def get_parameters(self):
        self.set_parameters("d0")
        return self.read_ser_buffer()

    def set_parameters(self, cmd_input: str = ""):
        """set a paramter as a string in the format:
        "[a-z][0-10000]"

        The serial command will be interpreted by the microcontroller as a command
        corresponding to the lower-case letter used, and a value given after it.
        Commands are processed by a semicolon, which is included by this function.
        """
        self.ser.write(f"{cmd_input};".encode("utf-8"))

        # return self.read_ser_buffer(timeout_s=2.0)

    def read_ser_buffer(self, timeout_s: float = 1.0):
        """reads incoming bytes and converts to string"""
        buffer = ""
        self.ser.write(b"g0;")

        timer = Timer(timeout_s)

        while ";" not in buffer and timer.running:
            resp = self.ser.read_until().decode("utf-8")

            if resp != "":
                buffer += resp
        
        


        return buffer

    def get_trace_data(self, timeout_s: float = 1.0):
        """
        sends retrieval command to tracecontroller, then reads the serial buffer
        and returns it as a string
        """
        buffer = self.read_ser_buffer(timeout_s)

        if len(buffer) < 100:
            status = 1
        else:
            status = 0

        return status, buffer


class Timer:
    def __init__(self, timeout_s: float = 1.0):
        self.start_time = time.time()
        self.timeout_s = timeout_s

    def restart(self):
        self.start_time = time.time()

    @property
    def running(self):

        time_elapsed = time.time() - self.start_time

        if time_elapsed > self.timeout_s:
            return False
        else:
            return True


# class DummyData:
#     """provides formatted lines of a previous datafile to mimic the ADC output"""

#     def __init__(self):
#         self.df = pd.read_csv(
#             "res\\030522_1542_4_0_testing0.csv",
#             skiprows=5,
#             names=["time_point", "time_us", "value"],
#         )

#     def get_row(self, idx):
#         return f"{idx}, {self.df.time_us[idx]}, {self.df.value[idx]} /r/n"


# class TraceControllerDebug:
#     def __init__(self, baud_rate: int = 115200, timeout: float = 1.0):
#         self.ser = None
#         self.connect_ser(baud_rate, timeout)
#         self.data = DummyData()
#         self.param_string = ""
#         logging.debug("and now we're done with init")

#     def connect_ser(self, baud_rate, timeout):
#         """
#         returns nothing! except for printing out some messages
#         """

#         logging.debug(f"connection to debug initiated.")
#         logging.debug(f"ser connected at debug")
#         logging.debug("so we're done with connect_sr")

#     def get_param_string(self):
#         return self.param_string

#     def get_diagnostic_info(self):
#         return "debug device interface"

#     def get_num_points(self):
#         return self.param_string

#     def get_parameters(self):
#         return self.param_string

#     def set_parameters(self, param_string):
#         """takes the command input string and parses it to set self.param values"""
#         self.param_string = param_string
#         return 1

#     def read_buffer(self):
#         return "read_buffer"

#     def receive_data(self) -> list:
#         """waits for data to be received from the ADC, then returns it as a list"""
#         strbuf = "0, 0, 0, 0"

#     def decode_data(self, buffer):
#         strbuf = "0, 0, 0, 0"

#     def get_trace_data(self, num_points):
#         """loads an old data file and then sends out line by line as if it was
#         imported data from the ADC"""

#         buffer = ""

#         for i in range(0, num_points):
#             buffer += self.data.get_row(i)

#         return buffer

#     def save_buffer_to_csv(self, wl, trace_buffer, trace_num, trace_note):
#         """give wavelength, str buffer of data, trace num, and note to save to csv"""

#         trace_date = time.strftime("%d%m%y")
#         trace_time = time.strftime("%H%M")

#         export_path = (
#             "./export/"
#             + trace_date
#             + "_"
#             + trace_time
#             + "_"
#             + wl
#             + "_"
#             + trace_note
#             + str(trace_num)
#         )
#         trace_filename = export_path + "dummy.csv"

#         # make the directory if it doesn't exist already
#         Path("./export/").mkdir(parents=True, exist_ok=True)

#         # write the data for this trace to disk
#         with open(trace_filename, "w") as f:
#             writer = csv.writer(f, delimiter=",")

#             writer.writerow(["num", "time_us", "value"])

#             for row in trace_buffer.split("/r/n"):
#                 writer.writerow(row.strip(" ").split(","))
#         f.close()
#         logging.debug(trace_filename)

#         return trace_filename
