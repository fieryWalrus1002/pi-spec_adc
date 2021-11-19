import time
import csv
from pathlib import Path
import pickle

class Action():
    def __init__(self, type, value):
        self.type = type
        self.value = value

class TraceParameters():
    def __init__(self, **kwargs):
        # TODO: add in the code that takes our string of paramaters and 
        # both submits it to the tracecontroller but also logs it here for easy reference. 
        # The tracecontroller will ask this object what num_points is for the datalogger module,
        # and we can have a function here that exports the settings for a data object in a 
        # human readable format
        self.num_points = kwargs.get('num_points', 2000)
        self.pulse_interval =  kwargs.get('pulse_interval', 248)
        self.gain_vis =  kwargs.get('gain_vis', 0)
        self.gain_ir = kwargs.get('gain_ir', 0)
        self.meas_led_vis =  kwargs.get('meas_led_vis',0)
        self.meas_led_ir =  kwargs.get('meas_led_ir', 4)
        self.pulse_length = kwargs.get('pulse_length', 50)
        self.sat_pulse_length =  kwargs.get('sat_pulse_length', 500)
        self.sat_trigger_point =  kwargs.get('sat_trigger_point', 900)
        self.act_int_phase =  kwargs.get('act_int_phase', [0, 0, 0])
        self.pulse_mode =  kwargs.get('pulse_mode', 1)
        self.trace_note = kwargs.get('trace_note', "")

    @property
    def parameter_string(self):
        string_list = [f"n{self.num_points}",
                         f"i{self.pulse_interval}",
                         f"g{self.gain_vis}", 
                         f"h{self.gain_ir}", 
                         f"v{self.meas_led_vis}",
                         f"r{self.meas_led_ir}",
                         f"p{self.pulse_length}",
                         f"s{self.sat_pulse_length}",
                         f"t{self.sat_trigger_point}",
                         f"w{self.act_int_phase[0]}",
                         f"x{self.act_int_phase[1]}",
                         f"y{self.act_int_phase[2]}",
                         f"z{self.pulse_mode}"]

        export_string = ""
        for string in string_list:
            export_string = export_string + string + ";"
        # print(export_string)
        # print("getter method called")

        return export_string


class Experiment():
    # an Experiment is a set of actions.
    # It can add actions to itself with these methods. 
    # An Experiment can be loaded or saved with Pickling, or saved as a CSV.
    # Actions can be any of these things:
    #   set_parameter, wait, light, execute_trace, save_data

    def __init__(self, datalogger, tracecontroller, log):
        self.datalogger = datalogger
        self.tracecontroller = tracecontroller
        self.log = log
        self.action_list = []
        self.trace_parameters = None # holds current trace_paramenters, updated frequently
        self.trace_cnt = 0 # the trace counter, increments for each trace executed
        self.data_list = [] # a list of data output from traces. each trace data is a dict
        # self.param_list = [] # a recorded list of trace_parameters for each trace
        
        
    # creates an action object and adds it to the action list
    # This list will be iterated through, with each set of instructions interpreted
    # by execute_trace() 
    def add_action(self, action_type, action_value):
        new_action = Action(type = action_type, value= action_value)
        self.action_list.append(new_action)

    def execute_action(self, action):
        print("executing action of type ", action.type, " _and a value of ", action.value)

        if action.type == "set_parameters":
            self.trace_parameters = action.value
           
            # update our variables on the arduino
            params_string = self.trace_parameters.parameter_string
            print(f"updating trace parameters: {params_string}")

            self.tracecontroller.set_parameters(params_string)

        elif action.type == "execute_trace":
            self.execute_trace()

        elif action.type == "save_data":
            self.save_data()

        elif action.type == "wait":
            self.wait(action.value)

        elif action.type == "end_step":
            print("Experiment Finished")
        else:
            pass
        
    
    
    def execute_trace(self):
        # set up the analog trace using num_points
        print("ready analog scan")
        self.datalogger.ready_scan(self.trace_parameters.num_points)
        
        # send the m command to arduino to execute the trace
        print("trigger trace")
        self.tracecontroller.set_parameters("m;")
        print("trig sent")
        
        # wait for trace to complete
        trace_length = (self.trace_parameters.num_points * (self.trace_parameters.pulse_interval * 0.000001))
        print(f"trace_length: {trace_length}s")
        time.sleep(trace_length * 1.1)

        # retrieve data from ADC
        data = []
        data = self.datalogger.get_data(self.trace_parameters.num_points)
        
        data_dict = {"trace_data" : data, "trace_params" : self.trace_parameters, "trace_num" : self.trace_cnt}

        self.data_list.append(data_dict)
        
        # increment trace counter
        self.trace_cnt += 1
        
    def save_data(self):
        print(f"save that data! found {len(self.data_list)} trace data to save")
        
        for data_dict in self.data_list:
            filename = self.datalogger.save_data_to_csv(data_dict["trace_data"], data_dict["trace_params"], data_dict["trace_num"])
            print(f"export: {filename}")

    def wait(self, wait_time):
        start_time = time.time()
        wait_time = float(wait_time)
        time_elapsed = 0
        self.log(f"waiting {wait_time} seconds \n")
        
        while time_elapsed <= wait_time:
            time.sleep(.01)
            time_elapsed = round(time.time() - start_time, 3)
        self.log(f"waited {time_elapsed} seconds \n")


class ExperimentHandler():
    # An object that carries instructions on how to execute a particular experiment,
    # and execute each step as required when it is told to begin. 
    # Multiple traces, wait periods, turning on and off actinic light.
    # Each trace is an object within a list, and there are instructions on what to do in between. 
    # There should be instructions on what to do with the data for each trace as well. 
    # It should write out a text copy of itself in some way. 

    # it will iterate through a list
    # each list item will be read and turned into an action: 
    #   - wait
    #   - turn on/off actinic or far red light
    #   - set parameters for a trace
    #   - execute a trace
    #   - save data to file, 
    def __init__(self, tracecontroller, datalogger, gui):
        # self.action_list = []
        self.tracecontroller = tracecontroller
        self.datalogger = datalogger
        self.experiment = None
        self.gui = gui
        self.log = gui.send_to_log
        self.prepare_example_experiments()

    def run_experiment(self):
        if self.experiment is None:
            print("No experiment loaded.")
        else:
            for action in self.experiment.action_list:
                self.experiment.execute_action(action)
                # action.execute_action(self.tracecontroller, self.datalogger

                # should be this instead:
                # action.run()

    def load_experiment(self, experiment):
        self.experiment = experiment
    
    def create_experiment_from_dict(self, dict):
        # create a trace paramter objects for experiment
        trace1 = TraceParameters(num_points=dict["num_points"], 
                                pulse_interval=dict["pulse_interval"], 
                                pulse_length=dict["pulse_length"],
                                meas_led_ir=dict["meas_led_ir"], 
                                meas_led_vis=dict["meas_led_vis"], 
                                gain_vis = dict["gain_vis"],
                                gain_ir = dict["gain_ir"],
                                act_int_phase=dict["act_int_phase"],
                                sat_trigger_point=dict["sat_trigger_point"],
                                sat_pulse_length=dict["sat_pulse_length"],
                                pulse_mode=dict["pulse_mode"],
                                trace_note = dict["trace_note"])
    
        
        print(trace1.parameter_string)

        # create an experiment object
        self.experiment = Experiment(datalogger=self.datalogger, tracecontroller=self.tracecontroller, log=self.log)           
        
        self.experiment.add_action("set_parameters", trace1)
        self.experiment.add_action(action_type="wait", action_value="1")
        self.experiment.add_action(action_type="execute_trace", action_value="0")
        self.experiment.add_action(action_type="save_data", action_value="0")
        self.experiment.add_action(action_type="end_step", action_value="0")
        
    def prepare_example_experiments(self):
        # create a trace paramter objects for experiment
        trace1 = TraceParameters(num_points=1000, 
                                pulse_interval=1000, 
                                pulse_length=50,
                                meas_led_ir=5, 
                                meas_led_vis=0, 
                                gain_vis = 0,
                                gain_ir = 0,
                                act_int_phase=[0, 0, 0],
                                sat_trigger_point=200,
                                sat_pulse_length=200,
                                pulse_mode=1,
                                trace_note = "800nm")
        
        trace2 = TraceParameters(num_points=1000, 
                                pulse_interval=1000, 
                                pulse_length=50,
                                meas_led_ir=6, 
                                meas_led_vis=0, 
                                gain_vis = 0,
                                gain_ir = 0,
                                act_int_phase=[0, 0, 0],
                                sat_trigger_point=200,
                                sat_pulse_length=200,
                                pulse_mode=1,
                                trace_note = "900nm")
        
        print(f"trace1: {trace1.parameter_string}")
        print(f"trace2: {trace2.parameter_string}")

        # create an experiment object
        p700_experiment = Experiment(datalogger=self.datalogger, tracecontroller=self.tracecontroller, log=self.log)           
        
        # add the actions of the experiment
        p700_experiment.add_action("set_parameters", trace1)
        p700_experiment.add_action(action_type="wait", action_value="1")
        p700_experiment.add_action(action_type="execute_trace", action_value="0")
        p700_experiment.add_action(action_type="save_data", action_value="0")
#         p700_experiment.add_action(action_type="wait", action_value="60")
        p700_experiment.add_action(action_type="wait", action_value="2")
        p700_experiment.add_action("set_parameters", trace2)
        p700_experiment.add_action(action_type="wait", action_value="1")
        p700_experiment.add_action(action_type="execute_trace", action_value="0")
        p700_experiment.add_action(action_type="save_data", action_value="0")
        
        p700_experiment.add_action(action_type="end_step", action_value="0")
        
        # add it to the experiment handler as the active experiment
        self.experiment = p700_experiment
        
        # experiment is created, save to disk
#         pickle.dump(p700_experiment, open( "p700_experiment.p", "wb" ) )
