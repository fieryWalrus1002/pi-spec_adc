import unittest
import time
import os
from src.datahandler import DataHandler


class TestDataHandler(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.datahandler = DataHandler()

    def test_init_experiment(self):
        today = time.strftime("%y%m%d")
        exp_name = "test_case"
        self.datahandler.init_experiment(exp_name)

        self.assertTrue(os.path.exists(f"/export/{today}_{exp_name}"))

    # def test_connect_adc(self):
    #     self.assertNotEqual(self.datalogger.adc, None)
    #     self.assertEqual(str(self.datalogger.adc)[0:13], "Serial<id=0xb")

    # def test_send_and_receive_commands(self):
    #     self.datalogger.send_command(cmd_input="s",value=0)
    #     recv = self.datalogger.listen_for_response()
    #     self.assertEqual("0\r\n", recv)

    # def test_get_data(self):
    #     data = self.datalogger.get_data(num_points=10, test=0)
    #     self.assertEqual(len(data), 10)


unittest.main()
