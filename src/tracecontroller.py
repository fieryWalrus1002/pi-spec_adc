import serial
import serial.tools.list_ports
import logging
import time


class TraceController:
    def __init__(self, baud_rate: int = 115200, timeout: float = 1.0):
        self.tcdev = None
        self.connect_tcdev(baud_rate, timeout)

    def connect_tcdev(self, baud_rate, timeout):
        """connects to microcontroller device with serial, returns connection to device

        Currently a chipkit MX3 from Digilent @ ttyUSB0, displays as:
        FT232R USB UART - FT232R USB UART ttyUSB0 /dev/ttyUSB0 1027 24577
        """

        for port in serial.tools.list_ports.comports():

            if port.vid == 1027:
                device = port.device
                logging.debug(device)

        while self.tcdev is None:
            logging.debug(f"connecting to tcdev at {device}...")
            self.tcdev = serial.Serial(device, baud_rate, timeout=timeout)

            if self.tcdev is None:
                time.sleep(1)
        time.sleep(12)
        logging.debug(f"tcdev connected at {device}")

    def get_diagnostic_info(self):
        return self.tcdev

    def get_num_points(self):
        self.set_parameters("d")
        time.sleep(0.25)
        recv = self.tcdev.readline()
        return recv

    def get_parameters(self):
        self.set_parameters("d0")
        time.sleep(0.25)
        params = self.receive_data(timeout=0.001)
        return params

    def set_parameters(self, cmd_input):
        cmd_output = str(cmd_input) + "\r"
        self.tcdev.write(cmd_output.encode("utf-8"))

    def read_buffer(self):
        recv = self.tcdev.readline()
        return recv

    def receive_data(self, timeout: float = 0.5) -> list:
        """waits for data to be received from the ADC, then returns it as a list"""
        buffer = ""
        recv = ""

        # read data from device
        start_time = time.time()
        timed_out = False

        while not timed_out:
            recv = self.tcdev.read_until().decode()

            buffer += recv

            current_time = time.time() - start_time

            if current_time > timeout:
                timed_out = True

        return buffer
