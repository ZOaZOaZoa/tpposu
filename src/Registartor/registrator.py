from Plant_API import Plant, Registrator, Channel, ChannelParam, TKI_step, Action, Preprocessing
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from time import perf_counter


class RegistratorGUI:
    def __init__(self, root):
        self.root = root
        self.running = False
        self.thread = None

        self.root.title("Регистрация измерений")

        # --- Количество кадров ---
        self.frame_count_label = ttk.Label(root, text="Сколько снять кадров?")
        self.frame_count_label.pack()

        self.frame_count_entry = ttk.Entry(root, width=20)
        self.frame_count_entry.pack()
        self.frame_count_entry.insert(0, "100")

        # --- Кнопки ---
        self.start_button = ttk.Button(root, text="Начать регистрацию", command=self.start)
        self.start_button.pack(pady=5)

        self.stop_button = ttk.Button(root, text="Остановить", command=self.stop)
        self.stop_button.pack(pady=5)

        # --- ФИО ---
        self.fio_label = ttk.Label(root, text="ФИО оператора:")
        self.fio_label.pack()

        self.fio_entry = ttk.Entry(root, width=40)
        self.fio_entry.pack()
        self.fio_entry.insert(0, "Иванов Иван")

        # --- Описание эксперимента ---
        self.description_label = ttk.Label(root, text="Описание эксперимента:")
        self.description_label.pack()

        self.description_entry = ttk.Entry(root, width=40)
        self.description_entry.pack()
        self.description_entry.insert(0, "Описания не задано")

        self.save_button = ttk.Button(root, text="Сохранить в БД", command=self.save)
        self.save_button.pack(pady=5)

        # --- Текущие измерения ---
        self.output_label = ttk.Label(root, text="Текущий кадр:")
        self.output_label.pack()

        self.output_text = tk.Text(root, height=30, width=80)
        self.output_text.pack()    
        self.save_button['state'] = tk.DISABLED

    def parse_frames_count(self):
        user_input = self.frame_count_entry.get()
        self.frames_count = None
        try:
            self.frames_count = int(user_input)
        except ValueError:
            messagebox.showerror("Ошибка", "В поле количества кадров введите число!")
        
        
        

    def start(self):
        if self.running:
            return
        
        self.parse_frames_count()
        if self.frames_count is None:
            return
        self.current_frame = 1

        self.registrator = init_registrator()
        self.running = True
        self.registrator.start_registration()

        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.registrator.stop_registration()

    def loop(self):
        self.should_update_output = True
        self.last_update_time = perf_counter()
        while self.running:
            self.registrator.measure_frame()
            self.save_button['state'] = tk.NORMAL

            if self.should_update_output:
                # обновление GUI
                self.update_output()
                self.last_update_time = perf_counter()

            current_time = perf_counter()
            time_unupdated = current_time - self.last_update_time
            self.should_update_output = time_unupdated > 1

            self.running = self.current_frame < self.frames_count
            self.current_frame += 1

        self.update_output()
        messagebox.showinfo("Успех", "Регистрация завершена!")

    def update_output(self):
        frame = self.registrator.last_frame
        channels_names = self.registrator.channels_names
        names = ['Номер кадра', 'Время замера кадра',] + channels_names

        if not frame:
            return

        texts = []
        for i in range(len(frame)):
            name = names[i]
            val = frame[i]
            if isinstance(val, float):
                texts.append(f'{name:>25}:{val:>30.2f}')
            else:
                texts.append(f'{name:>25}:{val:>30}')
        text = "\n".join(texts)

        def update():
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, text)

        self.root.after(0, update)

    def save(self):
        self.stop()
        fio = self.fio_entry.get()
        description = self.description_entry.get()

        try:
            self.registrator.save_to_db("measurements.db", fio, description)
            messagebox.showinfo("Успех", "Данные сохранены в БД")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

def init_registrator():
    # Определяем параметры и функции предобработки
    channels_params_list = [
        # (channel_num, 'function')
        (1, Preprocessing.PosControl,       ('CH1_RAW',),               (-25.0, 20.0)),
        (2, Preprocessing.No,               ('CH2_RAW',),               ()),
        (3, Preprocessing.No,               ('CH3_RAW',),               ()),
        (4, Preprocessing.PosControl,       ('CH4_RAW',),               (0.0, 1.0)),
        (5, Preprocessing.Norm,             ('CH5_NORM',),              (2.2, 1.5)),
        (6, Preprocessing.Mean,             ('CH6_MEAN', 'CH6_DISP'),   ()),
        (9, Preprocessing.StableControl,    ('CH9_VAL',),               ()),
        (16, Preprocessing.No,              ('CH16_RAW',),              ()),
        (46, Preprocessing.No,              ('CH46_RAW',),              ()),
        (66, Preprocessing.Formula,         ('CH66_FUNC',),             (86.0, 210.0)),
        (76, Preprocessing.StableControl,   ('CH76_VAL',),              ()),
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
    return registrator

if __name__ == '__main__':
    root = tk.Tk()
    app = RegistratorGUI(root)
    root.mainloop()