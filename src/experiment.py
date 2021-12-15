import time
import logging
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
        self.sat_pulse_end =  kwargs.get('sat_pulse_end', 20)
        self.sat_pulse_begin =  kwargs.get('sat_pulse_begin', 10)
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
                         f"s{self.sat_pulse_end}",
                         f"t{self.sat_pulse_begin}",
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

    def __init__(self, datalogger, tracecontroller):
        self.datalogger = datalogger
        self.tracecontroller = tracecontroller
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
            logging.debug(f"updating trace parameters: {params_string}")

            self.tracecontroller.set_parameters(params_string)
            

        elif action.type == "execute_trace":
            self.datalogger.ready_scan(num_points=self.trace_parameters.num_points)
            time.sleep(0.4)
            self.execute_trace()

        elif action.type == "save_data":
            self.save_data()

        elif action.type == "wait":
            self.wait(action.value)

        elif action.type == "end_step":
            logging.debug("Experiment Finished")
        else:
            pass
        
        
   
    
    def execute_trace(self):
        """ executes the programmed measurement trace, and saves data """
        # send the m command to tracecontroller to execute measurement trace
        self.tracecontroller.set_parameters("m;")
        logging.debug("trace executed, waiting for data")
        # retrieve data from ADC, in list form
        data = self.datalogger.receive_data(timeout=0.0001)
        
        logging.debug("data received")
        print(data)
        data_dict = {"trace_data" : data, "trace_params" : self.trace_parameters, "trace_num" : self.trace_cnt}

        self.data_list.append(data_dict)
        
        # increment trace counter
        self.trace_cnt += 1
        
    def save_data(self):
        logging.debug(f"save that data! found {len(self.data_list)} trace data to save")
        
        for data_dict in self.data_list:
            for item in data_dict["trace_data"]:
                print(item)

            filename = self.datalogger.save_data_to_csv(data_dict["trace_data"], data_dict["trace_params"], data_dict["trace_num"])
            logging.debug(f"export: {filename}")

    def wait(self, wait_time):
        start_time = time.time()
        wait_time = float(wait_time)
        time_elapsed = 0
                
        while time_elapsed <= wait_time:
            time.sleep(.01)
            time_elapsed = round(time.time() - start_time, 3)
        


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
    def __init__(self, tracecontroller, datalogger, gui=None):
        # self.action_list = []
        self.tracecontroller = tracecontroller
        self.datalogger = datalogger
        self.experiment = None
        
        self.experiment = self.prepare_example_experiments()
        self.gui = gui

            
            

    def debug_log(self, msg: str):
        """ logging.debug print to console when running in cli """
        logging.debug(msg)

    def run_experiment(self):
        if self.experiment is None:
            logging.debug("No experiment loaded.")
        else:
            for action in self.experiment.action_list:
                self.experiment.execute_action(action)

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
                                sat_pulse_begin=dict["sat_pulse_begin"],
                                sat_pulse_end=dict["sat_pulse_end"],
                                pulse_mode=dict["pulse_mode"],
                                trace_note = dict["trace_note"])
        
        
        # create an experiment object
        self.experiment = Experiment(datalogger=self.datalogger, tracecontroller=self.tracecontroller)           
        
        self.experiment.add_action("set_parameters", trace1)
        self.experiment.add_action(action_type="wait", action_value="1")
        self.experiment.add_action(action_type="execute_trace", action_value="0")
        self.experiment.add_action(action_type="save_data", action_value="0")
        self.experiment.add_action(action_type="end_step", action_value="0")
        
        return trace1
        
    def prepare_example_experiments(self) -> Experiment:
        # create a trace paramter objects for experiment
        trace1 = TraceParameters(num_points=1000, 
                                pulse_interval=250,
                                pulse_length=30,
                                meas_led_ir=5, 
                                meas_led_vis=0, 
                                gain_vis = 0,
                                gain_ir = 0,
                                act_int_phase=[0, 0, 0],
                                sat_pulse_begin=400,
                                sat_pulse_end=600,
                                pulse_mode=1,
                                trace_note = "800nm")
        
        trace2 = TraceParameters(num_points=1000, 
                                pulse_interval=250, 
                                pulse_length=30,
                                meas_led_ir=6, 
                                meas_led_vis=0, 
                                gain_vis = 0,
                                gain_ir = 0,
                                act_int_phase=[0, 0, 0],
                                sat_pulse_begin=400,
                                sat_pulse_end=600,
                                pulse_mode=1,
                                trace_note = "900nm")
        
        #logging.debug(f"trace1: {trace1.parameter_string}")
        #logging.debug(f"trace2: {trace2.parameter_string}")

        # create an experiment object
        p700_experiment = Experiment(datalogger=self.datalogger, tracecontroller=self.tracecontroller)           
        
        # add the actions of the experiment
        p700_experiment.add_action("set_parameters", trace1)
        p700_experiment.add_action(action_type="execute_trace", action_value="0")
        p700_experiment.add_action(action_type="save_data", action_value="0")
        p700_experiment.add_action("set_parameters", trace2)
        p700_experiment.add_action(action_type="execute_trace", action_value="0")
        p700_experiment.add_action(action_type="save_data", action_value="0")

        p700_experiment.add_action(action_type="end_step", action_value="0")
        
        # return this experiment
        return p700_experiment
        
        # experiment is created, save to disk
#         pickle.dump(p700_experiment, open( "p700_experiment.p", "wb" ) )
