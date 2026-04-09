from Plant import Plant
from typing import Callable

class Channel:
    def __init__(self, channel_num: int, plant: Plant, preproccess_function: str):
        self.channel = channel_num
        self.plant = plant
        self.value = []

        functions = {
            'norm': self._norm,
            'pos_control': self._pos_control,
            'stable_control': self._stable_control,
            'mean': self._mean,
            'formula': self._formula,
            'none': self._none,
        }
        self.preproccess_function = functions[preproccess_function]
    
    def measure(self):
        measurement = plant.measure(self.channel)
        self.value.append(measurement)
    
    def preproccess(self):
        self.preproccess_function()
    
    def _norm(self):
        raise NotImplemented()
    
    def _pos_control(self):
        print("Нужно реализовать _pos_control!!!")
    
    def _stable_control(self):
        raise NotImplemented()
    
    def _mean(self):
        raise NotImplemented()
    
    def _formula(self):
        raise NotImplemented()
    
    def _none(self):
        pass

class Frame:
    def __init__(self, channels_params: list[int, str], plant: Plant):
        # Создаём объекты каналов
        self.channels: dict[int, Channel] = dict()
        for channel_num, preprocess_function in channels_params:
            self.channels[channel_num] = Channel(channel_num, plant, preprocess_function)

        self.TKI: list[Callable[None, None]] = [
            self.channels[1].measure,
            self.channels[1].preproccess_function,
            self.channels[4].measure,
            self.channels[4].preproccess_function,
            #....TODO всю ТКИ
        ]

    def measure(self):
        for action in self.TKI:
            action()
    

        

def measure_frame(channels_params: list[int, str], plant: Plant) -> Frame:
    frame = Frame(channels_params, plant)
    frame.measure()
    return frame


# TODO
def start_registration():
    raise NotImplemented()

def stop_registration():
    raise NotImplemented()

def save_to_DB():
    raise NotImplemented()

if __name__ == '__main__':
    plant = Plant()

    # Определяем параметры и функции предобработки
    channels_params = [
        # (channel_num, 'function')
        (1, 'pos_control'),
        (2, 'none'),
        (3, 'none'),
        (4, 'pos_control'),
        #.... TODO все каналы
    ]

    frames = []
    for _ in range(100):
        frames.append(measure_frame(channels_params, plant))

    print(frames[0].channels[1].value)
    