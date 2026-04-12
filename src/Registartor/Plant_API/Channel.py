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

class Preprocessing(Enum):
    Norm = auto()
    PosControl = auto()
    StableControl = auto()
    Mean = auto()
    Formula = auto()
    No = auto()

class Channel:
    def __init__(self, channel_num: int, plant: Plant, preproccess_function: str):
        self.channel = channel_num
        self.plant = plant
        self.raw_measurements = []
        self.current_measurement = []
        self.control_fail_connections: list[Callable[[], None]] = []

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
        self.raw_measurements = []

    def control_fail_callbacks(self, func: Callable[[], None]):
        self.control_fail_callbacks.append(func)
    
    def _callback(self):
        for callback in self.control_fail_callbacks:
            callback()

    def _norm(self):
        measurement = ( self.raw_measurements[0] - 2.2) / 1.5
        
        self.current_measurement = [ measurement, ]
    
    def _pos_control(self):
        measurement = self.raw_measurements[0]
        if not (0 <= measurement and measurement <= 1):
            self._callback()
        
        self.current_measurement = [ measurement, ]
    
    def _stable_control(self):
        MAX_DIFFERENCE = 0.01

        for i in range(len(self.raw_measurements) - 1):
            difference = self.raw_measurements[i] - self.raw_measurements[i + 1]
            if abs(difference) >= MAX_DIFFERENCE:
                self._callback()

        self.current_measurement = [ self.raw_measurements[-1], ]
    
    def _mean(self):
        mean = statistics.mean(self.raw_measurements)
        var = statistics.variance(self.raw_measurements)
        self.current_measurement = [ mean, var ]
    
    def _formula(self):
        measurement = self.raw_measurements[0]
        self.current_measurement = [ ( measurement + 86 ) / ( measurement - 210 ), ]
    
    def _none(self):
        self.current_measurement = [ self.raw_measurements[0], ]
