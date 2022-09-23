import serial
import serial.tools.list_ports
import logging
import time
from threading import Thread


class TraceController:
    def __init__(self, baud_rate: int = 115200, timeout: float = 1.0):
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.device = self.get_device_port()
        self.ser = self.connect_to_device()
        self.data = []
        self.daemon = Thread(daemon=True, target=self.check_conn_status)
        self.daemon.start()
        self.max_intensity = 255  # limit on how high you can set the actinic, in 0-255

    def check_conn_status(self, interval_sec: float = 0.25):
        while True:
            if self.connected == False:
                self.ser = self.connect_to_device()
            time.sleep(interval_sec)

    def connect_to_device(self):
        ser = None

        while ser is None:
            ser = serial.Serial(
                port=self.device,
                baudrate=self.baud_rate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
            time.sleep(0.2)

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

    def switch_pulser_power(self, power: bool, timeout: int = 10000) -> str:

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
        time.sleep(0.25)
        recv = self.ser.readline()
        return recv

    def get_parameters(self):
        self.set_parameters("d0")
        time.sleep(0.25)
        params = self.ser.readline().decode("utf-8")
        return params

    def set_parameters(self, cmd_input: str = ""):
        """ set a paramter as a string in the format: 
            "[a-z][0-10000]"

            The serial command will be interpreted by the microcontroller as a command
            corresponding to the lower-case letter used, and a value given after it. 
            Commands are processed by a semicolon, which is included by this function.
            """
        cmd_output = f"{cmd_input};"
        self.ser.write(cmd_output.encode("utf-8"))
        return cmd_output

    def read_ser_buffer(self, timeout: int = 100000):
        """reads incoming bytes and converts to string"""
        timeout_cnt = 0
        recv = bytearray()
        recv_state = True
        buffer = ""

        while recv_state:
            if self.ser.in_waiting > 0:
                recv.extend(self.ser.read_all())
                try:
                    decoded = recv.decode()
                except UnicodeDecodeError:
                    logging.debug("unicode error")
                    print("unicode error")

                if len(decoded) > 1:
                    buffer += decoded
                    timeout_cnt = 0
                    recv = bytearray()

            timeout_cnt += 1

            if timeout_cnt > timeout:
                if len(buffer) < 1000:
                    # timeout with lack of data
                    return 1, buffer
                else:
                    # timeout, but a good size buffer
                    return 0, buffer

        return 0, buffer

    def get_trace_data(self, timeout: int = 10000):
        """
        sends retrieval command to tracecontroller, then reads the serial buffer
        and returns it as a string
        """
        self.set_parameters("g0")

        status, buffer = self.read_ser_buffer(timeout=timeout)

        return status, buffer

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
