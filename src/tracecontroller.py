import serial
import serial.tools.list_ports
import logging
import time

class TraceController():
    def __init__(self):
        self.tcdev = None
        self.connect_tcdev()

    def connect_tcdev(self):
        """ connects to microcontroller device with serial, returns connection to device
        
        Currently a chipkit MX3 from Digilent @ ttyUSB0, displays as:
        FT232R USB UART - FT232R USB UART ttyUSB0 /dev/ttyUSB0 1027 24577
        """

        for port in serial.tools.list_ports.comports():
            
            if port.vid == 1027:
                device = port.device
                logging.debug(device)

        while self.tcdev is None:
            logging.debug(f"connecting to tcdev at {device}...")
            self.tcdev = serial.Serial(device, 115200, timeout=1)

            if self.tcdev is None:
                time.sleep(1)

        logging.debug(f"tcdev connected at {device}")

    def get_diagnostic_info(self):
        return self.tcdev

    def get_num_points(self):
        self.set_parameters('d')
        time.sleep(.25)
        recv = self.tcdev.readline()
        return recv

    def set_parameters(self, cmd_input):
        cmd_output = cmd_input + '\r'
        self.tcdev.write(cmd_output.encode('utf-8'))

    def read_buffer(self):
        recv = self.tcdev.readline()
        return recv
        
  