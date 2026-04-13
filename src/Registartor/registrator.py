from Plant_API import Plant, Registrator, Channel, ChannelParam, TKI_step, Action, Preprocessing

def measure_frame(channels_params: list[tuple[int, str]], plant: Plant) -> Registrator:
    frame = Registrator(channels_params, plant)
    frame.measure_frame()
    return frame


# TODO
def start_registration():
    raise NotImplementedError()

def stop_registration():
    raise NotImplementedError()

def save_to_DB():
    raise NotImplementedError()

if __name__ == '__main__':
    # Определяем параметры и функции предобработки
    channels_params_list = [
        # (channel_num, 'function')
        (1, Preprocessing.PosControl,       ('CH1_RAW',),               (-25.0, 20.0)),
        (2, Preprocessing.No,               ('CH2_RAW',),               tuple()),
        (3, Preprocessing.No,               ('CH3_RAW',),               tuple()),
        (4, Preprocessing.PosControl,       ('CH4_RAW',),               (0.0, 1.0)),
        (5, Preprocessing.Norm,             ('CH5_NORM',),              (2.2, 1.5)),
        (6, Preprocessing.Mean,             ('CH6_MEAN', 'CH6_DISP'),   tuple()),
        (9, Preprocessing.StableControl,    ('CH9_VAL',),               tuple()),
        (16, Preprocessing.No,              ('CH16_RAW',),              tuple()),
        (46, Preprocessing.No,              ('CH46_RAW',),              tuple()),
        (66, Preprocessing.Formula,         ('CH66_FUNC',),             (86.0, 210.0)),
        (76, Preprocessing.StableControl,   ('CH76_VAL',),              tuple()),
    ]

    TKI_steps_params = [
        ( 1, Action.Measure),
        ( 1, Action.Preprocess),
        ( 4, Action.Measure),
        ( 4, Action.Preprocess),
        ( 6, Action.Measure),
        ( 9, Action.Measure),
        (76, Action.Measure),
        ( 2, Action.Measure),
        ( 3, Action.Measure),
        ( 6, Action.Measure),
        ( 9, Action.Measure),
        ( 9, Action.Preprocess),
        (76, Action.Measure),
        (16, Action.Measure),
        ( 5, Action.Measure),
        ( 5, Action.Preprocess),
        ( 6, Action.Measure),
        ( 9, Action.Measure),
        ( 9, Action.Preprocess),
        (76, Action.Measure),
        (76, Action.Preprocess),
        (46, Action.Measure),
        (66, Action.Measure),
        (66, Action.Preprocess),
        ( 6, Action.Measure),
        ( 9, Action.Measure),
        ( 9, Action.Preprocess),
        ( 6, Action.Measure),
        ( 6, Action.Preprocess),
        # (76, Action.Preprocess),
    ]

    channels_params = [ ChannelParam(*params) for params in channels_params_list ]
    tki_steps = [ TKI_step(*params) for params in TKI_steps_params ]

    plant = Plant()
    registrator = Registrator(channels_params, tki_steps, plant)

    for _ in range(100):
        registrator.measure_frame()
        print(registrator.last_frame)
    
    registrator.save_to_db('test.sqlite')