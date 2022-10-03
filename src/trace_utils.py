from dataclasses import dataclass
import time



@dataclass
class TraceParams:
    num_points: int = 10000
    pulse_interval: int = 100
    meas_led_ir: int = 5
    meas_led_vis: int = 0
    pulse_length: int = 50
    sat_pulse_begin: int = 500
    sat_pulse_end: int = 600
    pulse_mode: int = 1
    trigger_delay: int = 0
    trace_note: str = "debug"
    act_intensity: tuple = (1, 2, 3)

    @property
    def param_string(self):
        return f"r{self.meas_led_ir};v{self.meas_led_vis};n{self.num_points};z{self.pulse_mode};i{self.pulse_interval};p{self.pulse_length};e{self.trigger_delay};w{self.act_intensity[0]};x{self.act_intensity[1]};y{self.act_intensity[2]};"
    
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
    col_names: list = [
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

    def asdict(self) -> dict:
        return {"rep" : self.rep,
                "trace_num": self.trace_num,
                "trace_begun": self.trace_begun,
                "trace_end": self.trace_end,
                "param_string": self.param_string,
                "note": self.note,
                "created": self.created
        }

