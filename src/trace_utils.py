from dataclasses import dataclass
import time

@dataclass
class TraceParams:
    num_points: int = 1000
    pulse_interval: int = 500
    meas_led_ir: int = 0
    meas_led_vis: int = 0
    pulse_length: int = 50
    sat_pulse_begin: int = 400
    sat_pulse_end: int = 599
    pulse_mode: int = 1
    trigger_delay: int = 35
    trace_note: str = "debug"
    act_intensity: tuple = (0, 140, 0)
    detector_circuit: int = 0

    @property
    def param_string(self):
        # r0;v6;n1000;z1;i1000;p75;e35;w0;x140;y0;
        param_sub_str = [
            f"e{self.trigger_delay}",
            f"i{self.pulse_interval}",
            f"j{self.detector_circuit}",
            f"n{self.num_points}",
            f"p{self.pulse_length}",
            f"r{self.meas_led_ir}",
            f"s{self.sat_pulse_begin}",
            f"t{self.sat_pulse_end}",
            f"v{self.meas_led_vis}",
            f"w{self.act_intensity[0]}",
            f"x{self.act_intensity[1]}",
            f"y{self.act_intensity[2]}",
            f"z{self.pulse_mode}",
        ]
        return ";".join(param_sub_str)


@dataclass
class TraceData:
    """
    class for keepign track of trace data in an experiment.
    As a dataclass it can be returned with tracedata.asdict()

    params:
    rep: int          which rep of a particular trace
    buffer: str       The received data string from the uC
    trace_num: int    Which trace in chronological order receieved
    trace_begun: str  What time was the trace begun
    trace_end: str    what time did the trace end
    param_string: str What parameters were used for the trace
    note: str         Any user notes
    created: str = time.time()
    """

    rep: int
    buffer: str
    trace_num: int
    trace_begun: str
    trace_end: str
    param_string: str
    note: str
    created: float = time.time()
    col_names: list = (
        [
            "pt_num",
            "time_us",
            "paq_0",
            "paq_1",
            "paq_2",
            "aq_0",
            "aq_1",
            "aq_2",
            "aq_3",
            "aq_4",
            "aq_5",
        ],
    )

    def asdict(self) -> dict:
        return {
            "rep": self.rep,
            "trace_num": self.trace_num,
            "trace_begun": self.trace_begun,
            "trace_end": self.trace_end,
            "param_string": self.param_string,
            "note": self.note,
            "created": self.created,
        }
