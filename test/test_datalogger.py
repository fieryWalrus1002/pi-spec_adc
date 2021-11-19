import unittest
import logging
from src import tracecontroller
from src import datalogger

class TestDatalogger(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tracecontroller = tracecontroller.TraceController()
        cls.datalogger = datalogger.DataLogger()

    def test_connect_adc(self):
        self.assertNotEqual(self.datalogger.adc, None)
        self.assertEqual(str(self.datalogger.adc)[0:13], "Serial<id=0xb")

    def test_send_and_receive_commands(self):
        self.datalogger.send_command(cmd_input="s",value=0)
        recv = self.datalogger.listen_for_response()
        self.assertEqual("0\r\n", recv)

    def test_get_data(self):
        data = self.datalogger.get_data(num_points=10, test=0)
        self.assertEqual(len(data), 10)
    
unittest.main()
