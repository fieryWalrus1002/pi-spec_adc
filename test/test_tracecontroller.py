import unittest

from src import tracecontroller


class TestTracecontroller(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tracecontroller = tracecontroller.TraceController()

    def test_get_num_points(self):
        num_points = self.tracecontroller.get_num_points()
        self.assertEqual(b'', num_points)

    def test_diagnostic_info(self):
        tcdev = str(self.tracecontroller.get_diagnostic_info())
        self.assertEqual("Serial<id=0xb64", tcdev[0:15])

unittest.main()
