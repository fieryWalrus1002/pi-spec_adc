import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# from tkinter import *
from tkinter.messagebox import showinfo
import logging
from io import StringIO
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import argparse
import pandas as pd
import csv
import serial
from serial.serialutil import PARITY_NONE, STOPBITS_ONE
import serial.tools.list_ports
from src.datalogger import DataLogger
from src.tracecontroller import TraceController
from src.experiment import Action, TraceParameters, Experiment, ExperimentHandler
from threading import Thread, Event
from datetime import datetime
import re
import itertools
import time

# drawing heavy influence from https://github.com/qmylzq/tkinter-pyserial-tools/blob/e5c9dda56bbc9a3eeef205303f0096859c68de8e/tk_serial.py


#  # initalize the class
#   try:
#     usb1608FS = usb_1608FS()
#   except:
#     print('No USB-1608FS device found.')
#     return

# def read_buffer():


class LogUpdate(Thread):
    def __init__(self, window):
        Thread.__init__(self)
        # self.stopped = Event()
        self.parent = window

    def run(self):
        while True:
            # check the buffer every quarter second
            time.sleep(0.25)
            self.parent.check_buffer()


class PISPEC_APP:
    # this is the GUI
    def __init__(self, name):
        self.init_window_name = name
        self.datalogger = DataLogger()
        self.tracecontroller = TraceController()
        self.experimenthandler = ExperimentHandler(
            tracecontroller=self.tracecontroller, datalogger=self.datalogger, gui=self
        )

    def popup_bonus(self):
        win = tk.Toplevel()
        win.geometry("+1000+100")
        win.wm_title("Popup Window")

        l = tk.Label(win, text="Input")
        l.pack()

        b = ttk.Button(win, text="Close", command=win.destroy)
        b.pack()

    # Function for opening the
    # file explorer window
    def browse_for_csv(self):
        filename = filedialog.askopenfilename(
            initialdir="/home/pi/pispec_venv/export/",
            title="Select a File",
            filetypes=(("csv files", "*.csv*"), ("all files", "*.*")),
        )
        return filename

    def read_csv(self, filename):
        with open(filename) as csv_file:
            x_axis = []
            y_axis = []
            csv_reader = csv.reader(csv_file, delimiter=",")
            next(csv_reader)
            next(csv_reader)
            next(csv_reader)

            #             for row_num, row in enumerate(csv_reader, 1):
            #                 if row not in [['\n;'], ['sending data: 500 to 1000begin_data']]:
            for row in csv_reader:
                if len(row) > 1:
                    if row[1] != "":
                        x_axis.append(int(row[0]))
                        y_axis.append(int(row[1]))

        return x_axis, y_axis

    def plot_window(self):
        win = tk.Toplevel()
        win.geometry("500x500+1000+100")
        win.wm_title("Popup Window")

        filename = self.browse_for_csv()
        x_axis, y_axis = self.read_csv(filename)

        print(f"x len: {len(x_axis)}, y len: {len(y_axis)}")
        f = Figure(figsize=(3, 3), dpi=100)
        a = f.add_subplot(111)
        a.plot(x_axis, y_axis)
        print("plot done")

        canvas = FigureCanvasTkAgg(f, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        print("canvas draw done")
        toolbar = NavigationToolbar2Tk(canvas, win)
        toolbar.update()
        canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        print("finished")

    def create_menubar(self):
        menubar = tk.Menu(self.init_window_name)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New", command=self.donothing)
        filemenu.add_command(label="Open", command=self.donothing)
        filemenu.add_command(label="Save", command=self.donothing)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.init_window_name.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        testingmenu = tk.Menu(menubar, tearoff=0)
        # testingmenu.add_command(label="Load Gain Experiment", command=lambda: self.experimenthandler.create_gain_experiment(gain_selected.get()))
        testingmenu.add_command(
            label="Run Experiment", command=self.experimenthandler.run_experiment
        )
        menubar.add_cascade(label="Testing", menu=testingmenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Help Index", command=self.donothing)
        helpmenu.add_command(label="About...", command=self.donothing)
        menubar.add_cascade(label="Help", menu=helpmenu)

        self.init_window_name.config(menu=menubar)

    def donothing(self):
        pass

    def set_init_window(self):

        self.init_window_name.title("pi-spec")
        self.init_window_name.geometry("+200+200")
        self.init_window_name["bg"] = "lightgrey"

        # self.init_window_name.attributes('-alpha', -1)

        #### frame for buttons
        frame1 = tk.Frame(self.init_window_name, padx=5, pady=5)
        frame1.grid(row=1, column=0)
        # frame1.pack(side=TOP)

        # # frame for parameters
        frame2 = tk.Frame(self.init_window_name, padx=5, pady=5)
        frame2.grid(row=0, column=0)
        # frame2.pack(side=BOTTOM)

        # frame for log
        # frame3 = Frame(self.init_window_name, padx=5, pady=5)
        # frame3.grid(row=2, column=0)

        # "num_points":self.num_points_var.get(),
        num_points_label = tk.Label(frame2, text="num_points: ")
        num_points_label.grid(row=0, column=0)
        self.num_points_var = tk.IntVar()
        self.num_points_var.set(1000)
        self.num_points_entry = tk.Entry(frame2, textvariable=self.num_points_var)
        self.num_points_entry.grid(row=1, column=0)

        # create pulse interval selection menu
        # "pulse_interval":self.pulse_interval_var.get(),
        pulse_interval_options = [250, 500, 1000]
        self.pulse_interval_var = tk.IntVar()
        self.pulse_interval_var.set(1000)
        pulse_interval_label = tk.Label(frame2, text="pulse_interval: ")
        pulse_interval_label.grid(row=0, column=1)
        pulse_interval_drop_menu = tk.OptionMenu(
            frame2, self.pulse_interval_var, *pulse_interval_options
        )
        pulse_interval_drop_menu.grid(row=1, column=1)

        # create pulse length selection menu
        # "pulse_length":self.pulse_length_var.get(),
        pulse_length_options = [35, 50, 75]
        self.pulse_length_var = tk.IntVar()
        self.pulse_length_var.set(50)
        pulse_length_label = tk.Label(frame2, text="pulse_length: ")
        pulse_length_label.grid(row=0, column=2)
        pulse_length_drop_menu = tk.OptionMenu(
            frame2, self.pulse_length_var, *pulse_length_options
        )
        pulse_length_drop_menu.grid(row=1, column=2)

        # "act_int_phase":self.act_int_phase_var.get().split(",")
        act_int_phase_label = tk.Label(frame2, text="act_int_phase: ")
        act_int_phase_label.grid(row=0, column=3)
        self.act_int_phase_var = tk.StringVar()
        self.act_int_phase_var.set("0,0,0")
        self.act_int_phase_entry = tk.Entry(frame2, textvariable=self.act_int_phase_var)
        self.act_int_phase_entry.grid(row=1, column=3)

        # "sat_trigger_point":self.sat_trigger_point_var.get()
        sat_trigger_point_label = tk.Label(frame2, text="sat_trigger_point: ")
        sat_trigger_point_label.grid(row=0, column=4)
        self.sat_trigger_point_var = tk.IntVar()
        self.sat_trigger_point_var.set(200)
        self.sat_trigger_point_entry = tk.Entry(
            frame2, textvariable=self.sat_trigger_point_var
        )
        self.sat_trigger_point_entry.grid(row=1, column=4)

        # "sat_pulse_length":self.sat_pulse_length_var.get()
        sat_pulse_length_label = tk.Label(frame2, text="sat_pulse_length: ")
        sat_pulse_length_label.grid(row=0, column=5)
        self.sat_pulse_length_var = tk.IntVar()
        self.sat_pulse_length_var.set(200)
        self.sat_pulse_length_entry = tk.Entry(
            frame2, textvariable=self.sat_pulse_length_var
        )
        self.sat_pulse_length_entry.grid(row=1, column=5)

        # create vis_led button
        # "meas_led_vis":self.vis_LED_selected.get(),
        vis_LED_options = [0, 1, 2, 3, 4, 5, 6, 7]
        self.vis_LED_selected = tk.IntVar()
        self.vis_LED_selected.set(0)
        vis_LED_label = tk.Label(frame2, text="vis_LED: ")
        vis_LED_label.grid(row=2, column=1)
        vis_LED_drop_menu = tk.OptionMenu(
            frame2, self.vis_LED_selected, *vis_LED_options
        )
        vis_LED_drop_menu.grid(row=3, column=1)

        # "gain_vis":self.gain_vis_selected.get(),
        gain_vis_options = [0, 1, 2, 3, 4, 5, 6, 7]
        self.gain_vis_selected = tk.IntVar()
        self.gain_vis_selected.set(0)
        gain_vis_label = tk.Label(frame2, text="vis_gain: ")
        gain_vis_label.grid(row=2, column=2)
        gain_vis_drop_menu = tk.OptionMenu(
            frame2, self.gain_vis_selected, *gain_vis_options
        )
        gain_vis_drop_menu.grid(row=3, column=2)

        # create ir_LED button

        # "meas_led_ir":self.meas_led_ir_var.get(),
        ir_LED_options = [0, 1, 2, 3, 4, 5, 6, 7]
        self.ir_LED_selected = tk.IntVar()
        self.ir_LED_selected.set(0)
        ir_LED_label = tk.Label(frame2, text="ir_LED: ")
        ir_LED_label.grid(row=2, column=3)
        ir_LED_drop_menu = tk.OptionMenu(frame2, self.ir_LED_selected, *ir_LED_options)
        ir_LED_drop_menu.grid(row=3, column=3)

        # gain_ir drop down menu
        # "gain_ir":self.gain_ir_selected.get(),
        gain_ir_options = [0, 1, 2, 3, 4, 5, 6, 7]
        self.gain_ir_selected = tk.IntVar()
        self.gain_ir_selected.set(0)
        gain_ir_label = tk.Label(frame2, text="ir_gain: ")
        gain_ir_label.grid(row=2, column=4)
        gain_ir_drop_menu = tk.OptionMenu(
            frame2, self.gain_ir_selected, *gain_ir_options
        )
        gain_ir_drop_menu.grid(row=3, column=4)

        # pulse_mode drop down menu
        # "pulse_mode":self.pulse_mode_var.get(),
        pulse_mode_options = [0, 1, 2]
        self.pulse_mode_var = tk.IntVar()
        self.pulse_mode_var.set(1)
        pulse_mode_label = tk.Label(frame2, text="pulse_mode: ")
        pulse_mode_label.grid(row=2, column=5)
        pulse_mode_option_menu = tk.OptionMenu(
            frame2, self.pulse_mode_var, *pulse_mode_options
        )
        pulse_mode_option_menu.grid(row=3, column=5)

        # notes field
        # "trace_note":self.note_var.get()
        note_label = tk.Label(frame2, text="trace_note: ")
        note_label.grid(row=2, column=6)
        self.note_var = tk.StringVar()
        self.note_entry = tk.Entry(frame2, textvariable=self.note_var)
        self.note_entry.grid(row=3, column=6)

        # load custom experiment button
        load_experiment_button = tk.Button(
            frame1, text="Load Experiment", command=self.load_experiment
        )
        load_experiment_button.grid(row=0, column=1, padx=5, pady=5, sticky=tk.E + tk.W)

        # run experiment button
        run_experiment_button = tk.Button(
            frame1, text="Run Experiment", command=self.run_experiment
        )
        run_experiment_button.grid(row=0, column=2, padx=5, pady=5, sticky=tk.E + tk.W)

        # popup window button
        #         self.button_bonus = ttk.Button(frame1, text="Popup Window", command=self.popup_bonus)
        #         self.button_bonus.grid(row=0, column=3, padx=5, pady=5, sticky=tk.E+tk.W)
        self.button_bonus = ttk.Button(
            frame1, text="Popup Window", command=self.plot_window
        )
        self.button_bonus.grid(row=0, column=3, padx=5, pady=5, sticky=tk.E + tk.W)
        #         self.button_showinfo = ttk.Button(frame1, text="Show Info", command=self.popup_showinfo)
        #         self.button_showinfo.grid(row=0, column=4, padx=5, pady=5, sticky=tk.E+tk.W)
        #

        # #### Frame 3: result log ###
        self.result_text = scrolledtext.ScrolledText(frame1)
        self.result_text.grid(row=10, column=0, columnspan=3, padx=5, pady=5)
        # self.result_text.grid(row=10, column=0, columnspan=4, rowspan=5, padx=5, pady=5, sticky=tk.E+tk.W+S+N)

    def popup_showinfo(self):
        showinfo("Popup Window", "Hello World!")

    def load_experiment(self):
        # create a dict from the various variables and then send it to the experimenthandler to create an experiment from it
        act_int_phase_list = self.act_int_phase_var.get().split(",")

        for phase in range(0, len(act_int_phase_list)):
            act_int_phase_list[phase] = int(act_int_phase_list[phase])

        dict = {
            "num_points": int(self.num_points_var.get()),
            "pulse_interval": int(self.pulse_interval_var.get()),
            "pulse_length": int(self.pulse_length_var.get()),
            "meas_led_ir": self.ir_LED_selected.get(),
            "meas_led_vis": self.vis_LED_selected.get(),
            "gain_vis": self.gain_vis_selected.get(),
            "gain_ir": self.gain_ir_selected.get(),
            "act_int_phase": act_int_phase_list,
            "sat_trigger_point": int(self.sat_trigger_point_var.get()),
            "sat_pulse_length": int(self.sat_pulse_length_var.get()),
            "pulse_mode": self.pulse_mode_var.get(),
            "trace_note": self.note_var.get(),
        }

        # create an experiment from the variables above
        self.experimenthandler.create_experiment_from_dict(dict)

    def run_experiment(self):
        # run that experiment
        self.experimenthandler.run_experiment()

    # def send_to_tracecontroller(self):
    #     command = self.serial_cmd_input.get()
    #     self.tracecontroller.set_parameters(command)

    def check_buffer(self):
        recv = self.tracecontroller.read_buffer()
        self.send_to_log(recv)

    def send_to_log(self, value):
        self.result_text.insert("end", value)
        # self.result_text.see("end")
        self.result_text.update()


def start_window():
    print(
        "******************************** begin new run ******************************"
    )
    print(
        "*****************************************************************************"
    )
    root = tk.Tk()
    application = PISPEC_APP(root)
    application.set_init_window()
    application.create_menubar()

    t = LogUpdate(window=application)
    t.setDaemon(True)
    t.start()
    root.mainloop()


# start_window()


def main(pulse_interval: int = 500, trace_note: str = ""):
    ser = serial.Serial("/dev/ttyUSB0", 115200, timeout=1)
    time.sleep(5)
    buf = ""
    for _ in range(10):
        ser.write("d".encode())
        buf += str(ser.read())
        time.sleep(0.1)
    print(buf)


def calibrate_trigger_delay(
    datalogger, tracecontroller, num_points, meas_led_ir, meas_led_vis, pulse_length
):
    """ sets up datalogger for x points, then sets up tracecontroller to trigger several
    different very short protocols. max value returned from datalogger corresponds to
    best trigger_delay."""

    datalogger.ready_scan(num_points=num_points)
    tracecontroller.set_parameters("n", 1)
    tracecontroller.set_parameters("r", meas_led_ir)
    tracecontroller.set_parameters("v", meas_led_vis)
    tracecontroller.set_parameters("p", pulse_length)

    tracecontroller.set_parameters("c", num_points) # set the tracecontroller to init calibration

    wait_for_response(device=datalogger, timeout=2.0)

    datalogger._send_command("g", 0)
    data = datalogger.receive_data(timeout=2.0).strip(";")
    df = pd.read_table(StringIO(data), sep=",")
    df.columns =["cnt", "time_us", "acq_time", "value"]
    idx = df[["value"]].idxmax()
    new_trig_delay = int(df.iloc[idx]["cnt"]) * 2
    logging.debug(f"trigger_delay: {new_trig_delay} us")
    return new_trig_delay

def wait_for_response(device, timeout: float = 0.5):
    recv = ""
    while ";" not in recv:
        recv = device.receive_data(timeout=timeout)
    return recv


def main2(
    num_points: int,
    pulse_interval: int,
    meas_led_ir: int,
    meas_led_vis: int,
    pulse_length: int,
    sat_pulse_begin: int,
    sat_pulse_end: int,
    adc_timeout: float,
    pulse_mode: int,
    trigger_delay: int,
    trace_note: str,
):
    datalogger = DataLogger()
    tracecontroller = TraceController(baud_rate=9600)
    experimenthandler = ExperimentHandler(
        tracecontroller=tracecontroller, datalogger=datalogger,
    )

    

    trace1 = {
        "num_points": num_points,
        "pulse_interval": pulse_interval,
        "pulse_length": pulse_length,
        "meas_led_ir": meas_led_ir,
        "meas_led_vis": meas_led_vis,
        "gain_vis": 0,
        "gain_ir": 0,
        "act_int_phase": [0, 0, 0],
        "sat_pulse_begin": sat_pulse_begin,
        "sat_pulse_end": sat_pulse_end,
        "pulse_mode": pulse_mode,
        "trace_note": trace_note,
    }

    params = experimenthandler.create_experiment_from_dict(trace1)
    tracecontroller.set_parameters("r", meas_led_ir)
    tracecontroller.set_parameters("v", meas_led_vis)
    
    trigger_delay = calibrate_trigger_delay(datalogger=datalogger, tracecontroller = tracecontroller, num_points=20, meas_led_ir=meas_led_ir, meas_led_vis=meas_led_vis, pulse_length=pulse_length)
    
    tracecontroller.set_parameters("n", num_points)
    tracecontroller.set_parameters("z", pulse_mode)
    tracecontroller.set_parameters("i", pulse_interval)
    tracecontroller.set_parameters("p", pulse_length)
    tracecontroller.set_parameters("e", trigger_delay)
    tracecontroller.set_parameters("w", 0)
    tracecontroller.set_parameters("x", 0)
    tracecontroller.set_parameters("y", 0)
    tracecontroller.set_parameters("d", 0)
    logging.debug(tracecontroller.receive_data(timeout=0.5))

    

    trace_length = (num_points * pulse_interval) / 1000
    logging.debug(f"trace_length(s): {trace_length} ms")

    datalogger.ready_scan(num_points=num_points)
    logging.debug(datalogger.receive_data(timeout=0.5))

    tracecontroller.set_parameters("m", 0)
    print(wait_for_response(device=tracecontroller, timeout=0.5))
    print(wait_for_response(device=datalogger, timeout=2.0))

    datalogger._send_command("g", 0)
    data = datalogger.receive_data(timeout=adc_timeout)

    logging.debug(data[-100:-1])

    logging.debug("saving data")
    datalogger.save_buffer_to_csv(
        wl=(str(meas_led_vis) + "_" + str(meas_led_ir)),
        buffer=data,
        trace_num=0,
        trace_note="testing",
    )
    logging.debug("done")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(
        description="tests experiment execution and data logging from command line"
    )

    parser.add_argument(
        "-num_points",
        help="number of data points to gather in a trace",
        type=int,
        default=2000,
    )

    parser.add_argument(
        "-pulse_interval", help="pulse_interval in us", type=int, default=250,
    )

    parser.add_argument(
        "-meas_led_ir", help="meas_led_ir array number", type=int, default=5,
    )

    parser.add_argument(
        "-meas_led_vis", help="meas_led_vis array number", type=int, default=2,
    )

    parser.add_argument(
        "-pulse_length",
        help="how long, in us, is the measurement pulse length",
        type=int,
        default=5,
    )

    parser.add_argument(
        "-sat_pulse_begin",
        help="at what point does the saturation pulse turn on",
        type=int,
        default=400,
    )

    parser.add_argument(
        "-sat_pulse_end",
        help="at what point does the saturation pulse turn off",
        type=int,
        default=600,
    )

    parser.add_argument(
        "-adc_timeout",
        help="how long should we wait for data from the adc to be returned",
        type=float,
        default=2.0,
    )

    parser.add_argument(
        "-pulse_mode",
        help="0 for no sat pulse, 1 for sat pulse, 2 for stf",
        type=int,
        default=1,
    )

    parser.add_argument(
        "-trigger_delay",
        help="us delay from start of pulse to adc_trigger signal",
        type=int,
        default=25,
    )

    parser.add_argument(
        "-trace_note",
        help="note for trace file when saving this experiment",
        type=str,
        default="test",
    )

    args = parser.parse_args()

    main2(**vars(args))
