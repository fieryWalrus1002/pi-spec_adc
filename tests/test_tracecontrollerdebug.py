import unittest
import sys

sys.path.append("D:/projects/pi-spec-cli/src")

from src.tracecontroller import TraceControllerDebug


class TestTracecontrollerDebug(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tracecontroller = TraceControllerDebug()

    def test_single_param_set(self):
        result = self.tracecontroller.set_parameters("z0;")
        self.assertEqual(result, 1)

    def test_get_param_value(self):
        val_string = "101"
        set1 = self.tracecontroller.set_parameters(f"z1  ;r {val_string};")

        result = self.tracecontroller.params["r"]
        self.assertEqual(result, int(val_string))

    def test_get_param_string(self):
        param_string = "r0;v1;n2;z3;i4;p5;e6;"
        self.tracecontroller.set_parameters(param_string)
        new_param_string = self.tracecontroller.get_param_string()
        expected_string = "r: 0, v: 1, n: 2, z: 3, i: 4, p: 5, e: 6, w: 0, x: 0, y: 0,"
        self.assertEqual(expected_string.strip(" "), new_param_string.strip(" "))


unittest.main()
