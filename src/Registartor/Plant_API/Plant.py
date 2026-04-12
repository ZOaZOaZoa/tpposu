import ctypes
import os
from pathlib import Path

src_code_path = Path(__file__).parent.parent.parent

match os.name:
    case 'nt':
        # Windows
        PLANT_LIB_PATH = src_code_path / 'object' / 'bin' / 'plant.dll'
    case 'posix':
        # Linux
        PLANT_LIB_PATH = src_code_path / 'object' / 'bin' / 'libplant.so'


class Plant:
    def __init__(self):
        self.lib = ctypes.CDLL(PLANT_LIB_PATH)

        # Описание API
        self.Plant_type = ctypes.c_double * 53

        self.lib.plant_init.argtypes = [self.Plant_type]
        self.lib.plant_init.restype = None

        self.lib.plant_measure.argtypes = [ctypes.c_int, self.Plant_type]
        self.lib.plant_measure.restype = ctypes.c_double

        self.lib.plant_control.argtypes = [ctypes.c_int, ctypes.c_double, self.Plant_type]
        self.lib.plant_control.restype  = None

        self.plant = self.Plant_type()

        # Инициализация
        self.lib.plant_init(self.plant)

    def measure(self, channel: int) -> float:
        return self.lib.plant_measure(channel, self.plant)

    def control(self, channel: int, control: float) -> None:
        self.lib.plant_control(channel, control, plant)