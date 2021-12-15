import serial
import serial.tools.list_ports
import logging
import time

class TraceController():
    def __init__(self, baud_rate: int = 9600, timeout: float = 1.0):
        self.tcdev = None
        self.connect_tcdev(baud_rate, timeout)

    def connect_tcdev(self, baud_rate, timeout):
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
            self.tcdev = serial.Serial(device, baud_rate, timeout=timeout)

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
    
    def get_parameters(self):
        self.set_parameters("d0");
        time.sleep(0.25)
        params = self.receive_data(timeout=0.001)
        return params
    
    def set_parameters(self, cmd_input):
        cmd_output = str(cmd_input) + '\r'
        self.tcdev.write(cmd_output.encode('utf-8'))

    def read_buffer(self):
        recv = self.tcdev.readline()
        return recv
    
    def receive_data(self, timeout: float) -> list:
        """ waits for data to be received from the ADC, then returns it as a list """        
        data = []               
        buffer = ""
        recv = ""
        
        # read data from device
        start_time = time.process_time()
        while not self._timedout(timeout=timeout, start_time=start_time):
            recv = self.tcdev.read_until().decode()
            if ";" in recv:
                break
            buffer += recv

        data = buffer.split("\r\n")
        
        return data  
  
    def _timedout(self, start_time: float, timeout: float = 1.0) -> bool:
        """ checks to see if the while loop should timeout. Returns true if timeout is reached """
        # logging.debug(f"start_time: {start_time}, now: {time.process_time()}")
        return ((time.process_time() - start_time) >= timeout)