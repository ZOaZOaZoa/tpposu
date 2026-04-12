from Plant_API import Plant, Frame, Channel

def measure_frame(channels_params: list[tuple[int, str]], plant: Plant) -> Frame:
    frame = Frame(channels_params, plant)
    frame.measure()
    return frame


# TODO
def start_registration():
    raise NotImplementedError()

def stop_registration():
    raise NotImplementedError()

def save_to_DB():
    raise NotImplementedError()

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
    