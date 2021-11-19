from time import sleep
import serial
import time
import math
import random
import serial.tools.list_ports
from pathlib import Path
import csv
from datetime import datetime
import argparse
import logging

# ttyACM0 Seeeduino 
# ttyUSB0 MX3
# class DataLogger():
#     def __init__(self):
#           # initalize the class
# class DataDaemon(Thread):
#     def __init__(self, window):
#         Thread.__init__(self)
#         # self.stopped = Event()
#         self.parent = window

#     def run(self):
#         while True:
#             # check the buffer every quarter second
#             time.sleep(0.25)
#             self.parent.check_buffer()

class DataLogger():
    def __init__(self):
        self.adc = None
        self.packet_size = 1000
        self.connect_adc()

    def connect_adc(self):
        """ creates serial connection to ADC device """
        # ttyACM0 Seeeduino, vid 10374, pid 32815
        for port in serial.tools.list_ports.comports():
            if port.vid == 10374:
                device = port.device

        while self.adc is None:
            logging.debug("connecting to ADC")
            self.adc = serial.Serial(device, 4000000, timeout=1)

            if self.adc is None:
                sleep(1)

        logging.debug("ADC connected")
        

    def flush_buffer(self):
        self.adc.reset_input_buffer()

    def send_command(self, cmd_input, value):
        cmd_output = cmd_input + str(value) + ';'
        logging.debug(f"cmd_output to adc: {cmd_output}")
        
        self.adc.write(cmd_output.encode('utf-8'))
        logging.debug("written to adc")
        

    def query(self):
        self.send_command(cmd_input = "s", value = 0)
        recv = ''

        while self.adc.inWaiting() > 0:
            recv += self.adc.readline().decode('utf-8')
        return recv

    def listen_for_response(self):
        recv = ''
        while self.adc.inWaiting() > 0:
            recv += self.adc.readline().decode('utf-8')
        return recv

    def ready_scan(self, num_points):
        # send a command to the adc to prepare a scan with the given number of points
        self.send_command("r", num_points)

    def change_adc_channel(self, channel):
        print("change_adc_channel not a valid command")
        pass
    
    def get_data_old(self, num_points, test = 0, **kwargs):
        packet_size = kwargs.get('packet_size', 500) # either use this many points or whatever is specified in kwargs
        
        # get the data between 0 and num_points in a number of packets equal to the class variable packet_size
                
        # wait for the ADC to be ready to send over data
        data = []
        resp = ""
        i = 0
   
        while (resp == "") and (i < 10):
            time.sleep(.25)
            resp = self.listen_for_response()

        print("Data ready for retrieval: %s ." % resp)
        
        # set current_num to zero
        self.send_command("c", 0)
         
        # measure how much time it takes to get the data back
        begin = datetime.now()
         
        # how many packets are we requesting? round up to the next integer
        total_packets = math.ceil(num_points / packet_size) 
        
        # for each packet we get, add it to the packet_list
        packet_list = []
        
        # get data for each packet
        for packet in range(0, total_packets):
            # send get data command
            self.send_command("g", packet_size)
            
            # receive the data
            packet_list.append(self.adc.read_until(';').decode('utf-8').split('\r'))
            
        # how long did it take?    
        time_elapsed = datetime.now() - begin
        print("time elapsed: %f " % time_elapsed)
        
        # combine all the data from packets to a data file
        for packet in packet_list:
            for row in packet:
                data.append(row)
                                            
        print("recv data, length: %i, expected: %i" % len(data), num_points)

        return data

    def parse_raw(raw):
        """ parse bytes output from Arduino """
        raw = raw.decode()
        if raw[-1] != "\n":
            raise ValueError(
                "Input must end with newline, otherwise message is incomplete"
            )
        
        t, V = raw.rstrip().split(",")

        return int(t), int(V) * 3.3 / 4095

    def read_all(self, read_buffer=b"",):
        """ read all available bytes from the serial port and append to read buffer"""

        previous_timeout = self.adc.timeout
        self.adc.timeout = None

        in_waiting = self.adc.in_waiting
        read = self.adc.read(size=in_waiting)

        self.adc.timeout = previous_timeout

        return read_buffer + read

    def get_data(self, num_points: int = 10, test: int=0):
        buffer = b""
        logging.debug("buffer defined")
        self.send_command("g", num_points)
        logging.debug("send_command('g', num_points)")
        buffer = self.read_all(read_buffer=buffer)
        logging.debug("buffer read")
        return buffer


    # def get_data(self, num_points: int = 10, test: int = 0):
    #     point = []
    #     voltage = []

    #     # set current_num to zero
    #     self.send_command("c", 0)
         
    #     # measure how much time it takes to get the data back
    #     begin = datetime.now()         
        
    #     self.send_command("g", num_points)
        
    #     while i < num_points:
    #         raw = self.adc.read_until()

    #         try:
    #             t, V = parse_raw(raw)
    #             point[i] = t
    #             voltage[i] = V
    #         except:
    # #             pass
                
    #         packet = self.adc.read_until(';').decode('utf-8').split('\r')

    #         for row in packet:
    #             data.append(row)
            
    #     # how long did it take?    
    #     time_elapsed = datetime.now() - begin
        
    #     logging.debug(f"time elapsed: {time_elapsed}")
                                            
    #     logging.debug(f"recv data, length:{len(data)}, expected: {num_points}")
    #     print(data)
    #     return data

    def save_data_to_csv(self, trace_data, trace_params, trace_num):
        wl = str(trace_params.meas_led_vis) + str(trace_params.meas_led_ir)
        trace_date = time.strftime("%d%m%y")
        trace_time = time.strftime("%H%M")
        
        if trace_params.trace_note == "":
            trace_note = ""
        else:
            trace_note = str(trace_params.trace_note) + "_"

        export_path = "./export/" + trace_date + "_" + trace_time + "_" + wl + "_" + trace_note + str(trace_num)
        trace_filename = export_path + ".csv"

        # make the directory if it doesn't exist already
        Path("./export/").mkdir(parents=True, exist_ok=True)

        # write the data for this trace to disk
        with open(trace_filename,"a") as f:
            writer = csv.writer(f,delimiter=",")
            writer.writerow(["trace_params", trace_params.parameter_string])
            writer.writerow(["num", "voltage"])

            for row in trace_data:
                writer.writerow(row.split(','))
                # time.sleep(.001)
            
        f.close()

        return trace_filename

    def test(self, samples):
        errors = 0

        for i in range(0,samples):
            query_value = random.randint(0, 10)
            query_response = int(datalogger.query(query_value))
            
            if query_response != query_value:
                errors += 1
                print(query_value, query_response)
        
        error_rate = errors / samples
        
        print(f"errors= {errors}, error rate = {error_rate}")

# if __name__ == "__main__":

#     # try:
#     #     adc = serial.Serial('/dev/ttyACM0', 4000000, timeout=5)
#     # except:
#     #         print('adc fail')

#     for port in serial.tools.list_ports.comports():
#         if port.vid == 10374:
#             device = port.device
#     try:
#         datalogger = DataLogger(serial.Serial(device, 4000000, timeout=1))
    
#     except:
#         print("No XIAO device found.")

#     print(f"XIAO connected at {device}")


#     # datalogger.test(100)
#     recv_data = datalogger.get_data(1000, test=0)
#     print(len(recv_data), 1000)
#     for row in recv_data:
#         print(row)

def main(p: int):
    datalogger = DataLogger()
    logging.debug("getting data")
    data = datalogger.get_data(num_points=10, test=0)
    logging.debug("data acquired:")
    logging.debug(data)
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(
        description="tests experiment execution and data logging"
    )

    parser.add_argument(
        "-p",
        help="placeholder",
        type=int,
        default=0,
    )

    args = parser.parse_args()

    main(**vars(args))


