from .Plant import Plant
from enum import Enum, auto
from typing import Callable
from dataclasses import dataclass
import statistics

@dataclass
class ChannelParam:
    number: int
    preprocessing: Preprocessing
    columns_in_db: tuple[str]
    additional_params: tuple[float]

class Preprocessing(Enum):
    Norm = auto()
    PosControl = auto()
    StableControl = auto()
    Mean = auto()
    Formula = auto()
    No = auto()

class Channel:
    def __init__(self, channel_num: int, plant: Plant, preproccess_function: str, additional_params: tuple[float]):
        self.channel = channel_num
        self.plant = plant
        self.additional_params = additional_params
        self.raw_measurements = []
        self.current_measurement = []
        self.control_fail_callbacks: list[Callable[[], None]] = []

        functions = {
            Preprocessing.Norm: self._norm,
            Preprocessing.PosControl: self._pos_control,
            Preprocessing.StableControl: self._stable_control,
            Preprocessing.Mean: self._mean,
            Preprocessing.Formula: self._formula,
            Preprocessing.No: self._none,
        }
        self.preproccess_function = functions[preproccess_function]

    def measure(self):
        measurement = self.plant.measure(self.channel)
        self.raw_measurements.append(measurement)
    
    def preproccess(self):
        self.preproccess_function()

        if not self.preproccess_function.__name__ == '_stable_control':
            self.raw_measurements = []

    def connect_control_fail_callbacks(self, func: Callable[[], None]):
        self.control_fail_callbacks.append(func)
    
    def _callback(self):
        for callback in self.control_fail_callbacks:
            callback()

    def _norm(self):
        b1 = self.additional_params[0]
        b2 = self.additional_params[1]
        measurement = ( self.raw_measurements[0] - b1) / b2
        
        self.current_measurement = [ measurement, ]
    
    def _pos_control(self):
        b1 = self.additional_params[0]
        b2 = self.additional_params[1]
        measurement = self.raw_measurements[0]
        if not (b1 <= measurement and measurement <= b2):
            self._callback()
        
        self.current_measurement = [ measurement, ]
    
    def _stable_control(self):
        MAX_DIFFERENCE = 0.01

        difference = self.raw_measurements[-1] - self.raw_measurements[-2]
        if abs(difference) >= MAX_DIFFERENCE:
            self._callback()

        self.current_measurement = [ self.raw_measurements[-1], ]
        self.raw_measurements = [ self.raw_measurements[-1], ]
    
    def _mean(self):
        mean = statistics.mean(self.raw_measurements)
        var = statistics.variance(self.raw_measurements)
        self.current_measurement = [ mean, var ]
    
    def _formula(self):
        b1 = self.additional_params[0]
        b2 = self.additional_params[1]

        measurement = self.raw_measurements[0]
        self.current_measurement = [ ( measurement + b1 ) / ( measurement - b2 ), ]
    
    def _none(self):
        self.current_measurement = [ self.raw_measurements[0], ]
