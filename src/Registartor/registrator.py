from .Plant_API import Plant, Registrator, ChannelParam, TKI_step, Action, Preprocessing, MeasureError
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from time import perf_counter

class RegistratorGUI:
    def __init__(self, parent=None, tab_name: str = ''):
        self.parent = parent
        self.running = False
        self.thread = None
        self.title = "Регистрация измерений"
        self.measurement_data = []  # Хранилище всех измерений
        self._setup_ui()

    def _setup_ui(self):
        """Настройка пользовательского интерфейса"""
        
        # Основной контейнер с возможностью изменения размера
        self.main_paned = ttk.PanedWindow(self.parent, orient=tk.VERTICAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Верхняя панель (фиксированная часть)
        self.top_container = ttk.Frame(self.main_paned)
        self.main_paned.add(self.top_container, weight=0)
        
        # Панель параметров регистрации
        self.params_frame = ttk.LabelFrame(self.top_container, text="Параметры регистрации", padding=10)
        self.params_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Центрируем содержимое
        params_inner_frame = ttk.Frame(self.params_frame)
        params_inner_frame.pack(anchor=tk.CENTER)
        
        # Количество кадров
        ttk.Label(params_inner_frame, text="Количество кадров:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.frame_count_entry = ttk.Entry(params_inner_frame, width=20)
        self.frame_count_entry.grid(row=0, column=1, padx=5, pady=5)
        self.frame_count_entry.insert(0, "100")
        
        # ФИО оператора
        ttk.Label(params_inner_frame, text="ФИО оператора:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.fio_entry = ttk.Entry(params_inner_frame, width=40)
        self.fio_entry.grid(row=1, column=1, padx=5, pady=5)
        self.fio_entry.insert(0, "Иванов Иван")
        
        # Описание эксперимента
        ttk.Label(params_inner_frame, text="Описание эксперимента:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.description_entry = ttk.Entry(params_inner_frame, width=40)
        self.description_entry.grid(row=2, column=1, padx=5, pady=5)
        self.description_entry.insert(0, "Описания не задано")
        
        # Панель управления (кнопки)
        self.control_frame = ttk.Frame(self.top_container)
        self.control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Центрируем кнопки
        buttons_inner_frame = ttk.Frame(self.control_frame)
        buttons_inner_frame.pack(anchor=tk.CENTER)
        
        self.start_button = ttk.Button(buttons_inner_frame, text="Начать регистрацию", command=self.start, width=20)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(buttons_inner_frame, text="Остановить", command=self.stop, width=20)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.save_button = ttk.Button(buttons_inner_frame, text="Сохранить в БД", command=self.save, width=20)
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.save_button['state'] = tk.DISABLED
        
        # Кнопка очистки таблицы
        self.clear_button = ttk.Button(buttons_inner_frame, text="Очистить таблицу", command=self.clear_table, width=20)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Панель таблицы измерений (растягивается)
        self.table_container = ttk.Frame(self.main_paned)
        self.main_paned.add(self.table_container, weight=1)
        
        # Создаем фрейм для таблицы
        self.table_frame = ttk.LabelFrame(self.table_container, text="Таблица измерений", padding=10)
        self.table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Создаем Treeview с прокруткой
        self.tree_frame = ttk.Frame(self.table_frame)
        self.tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(self.tree_frame, show='headings')
        self.tree.tag_configure('error', background='red')
        self.vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        self.vsb.grid(row=0, column=1, sticky='ns')
        self.hsb.grid(row=1, column=0, sticky='ew')
        
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        
        # Статусная строка
        self.status_frame = ttk.Frame(self.table_container)
        self.status_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.status_label = ttk.Label(self.status_frame, text="Готов к работе", font=('Arial', 9))
        self.status_label.pack(side=tk.LEFT)
        
        self.progress_label = ttk.Label(self.status_frame, text="", font=('Arial', 9))
        self.progress_label.pack(side=tk.RIGHT)

    def clear_table(self):
        """Очистка таблицы и данных"""
        if self.running:
            messagebox.showwarning("Предупреждение", "Остановите регистрацию перед очисткой таблицы")
            return
        
        self.measurement_data.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.status_label.config(text="Таблица очищена")
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
        
        # Очищаем предыдущие данные
        self.clear_table()
        
        self.current_frame = 1
        self.registrator: Registrator = self.init_registartor()
        self.running = True
        self.registrator.start_registration()
        
        # Настройка колонок таблицы
        self.setup_table_columns()
        
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()
        
        self.status_label.config(text="Регистрация запущена...")

    def setup_table_columns(self):
        """Настройка колонок таблицы на основе каналов регистратора"""
        channels_names = self.registrator.channels_display_names
        columns = ['Кадр', 'Время замера'] + channels_names
        
        self.tree['columns'] = columns
        
        # Настройка каждой колонки
        for col in columns:
            self.tree.heading(col, text=col)
            
            # Устанавливаем ширину колонок
            if col == 'Номер кадра':
                width = 100
            elif col == 'Время замера':
                width = 150
            else:
                width = 120
            
            self.tree.column(col, width=width, minwidth=80, anchor='center')

    def stop(self):
        self.running = False
        if hasattr(self, 'registrator'):
            self.registrator.stop_registration()
        self.status_label.config(text="Регистрация остановлена")

    def loop(self):
        self.last_update_time = perf_counter()
        
        while self.running and self.current_frame <= self.frames_count:
            self.registrator.measure_frame()
            
            # Добавляем измерение в таблицу
            self.add_measurement_to_table()
            
            # Обновляем прогресс
            def update_progress():
                progress_text = f"Кадр {self.current_frame} из {self.frames_count}"
                self.progress_label.config(text=progress_text)
                self.save_button['state'] = tk.NORMAL
            self.parent.after(0, update_progress)
            
            self.current_frame += 1
            
            # Небольшая задержка для предотвращения зависания GUI
            time.sleep(0.01)
        
        def show_complete():
            if self.current_frame > self.frames_count:
                messagebox.showinfo("Успех", "Регистрация завершена!")
                self.status_label.config(text="Регистрация завершена")
                self.progress_label.config(text=f"Завершено: {self.frames_count} кадров")
        
        self.parent.after(0, show_complete)
        self.running = False

    def add_measurement_to_table(self):
        """Добавление текущего измерения в таблицу"""
        frame = self.registrator.last_frame
        
        if not frame:
            return
        
        # Формируем строку данных
        row_data = []
        row_data.append(str(frame[0]))  # Номер кадра
        row_data.append(str(frame[1]))  # Время замера
        
        # Добавляем значения каналов
        for i in range(2, len(frame)):
            val = frame[i]
            if isinstance(val, float):
                row_data.append(f"{val:.4f}")
            else:
                row_data.append(str(val))
        
        # Добавляем в таблицу в главном потоке
        def add_row():
            # Вставляем в начало таблицы (сверху новые кадры)
            tags = list()
            if self.registrator.measure_status == MeasureError.PosControl:
                tags.append('error')
            self.tree.insert('', 'end', values=row_data, tags=tags)
            
            # Автопрокрутка к новому элементу
            self.tree.yview_moveto(1)
        
        self.parent.after(0, add_row)

    def save(self):
        if self.running:
            reply = messagebox.askyesno("Подтверждение", 
                                        "Регистрация еще выполняется. Остановить и сохранить?")
            if reply:
                self.stop()
            else:
                return
        
        if not self.measurement_data and not hasattr(self, 'registrator'):
            messagebox.showwarning("Предупреждение", "Нет данных для сохранения")
            return
        
        fio = self.fio_entry.get()
        description = self.description_entry.get()

        try:
            self.registrator.save_to_db("measurements.db", fio, description)
            messagebox.showinfo("Успех", "Данные сохранены в БД")
            self.status_label.config(text="Данные сохранены в БД")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def init_registartor(self) -> Registrator:
        # Определяем параметры и функции предобработки
        channels_params_list = [
            # (channel_num, 'function')
            (1, Preprocessing.PosControl,       ('CH1_RAW',),               (-25.0, 20.0)),
            (2, Preprocessing.No,               ('CH2_RAW',),               ()),
            (3, Preprocessing.No,               ('CH3_RAW',),               ()),
            (4, Preprocessing.PosControl,       ('CH4_RAW',),               (0.0, 1.0)),
            (5, Preprocessing.Norm,             ('CH5_NORM',),              (2.2, 1.5)),
            (6, Preprocessing.Mean,             ('CH6_MEAN', 'CH6_DISP'),   ()),
            (9, Preprocessing.StableControl,    (),                         ()),
            (16, Preprocessing.No,              ('CH16_RAW',),              ()),
            (46, Preprocessing.No,              ('CH46_RAW',),              ()),
            (66, Preprocessing.Formula,         ('CH66_FUNC',),             (86.0, 210.0)),
            (76, Preprocessing.StableControl,   (),                         ()),
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