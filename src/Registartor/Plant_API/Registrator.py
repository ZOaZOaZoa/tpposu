from .Channel import Channel, ChannelParam, MeasureError, Preprocessing
from .Plant import Plant
from dataclasses import dataclass
from typing import Any
from enum import Enum, auto
from contextlib import contextmanager
import sqlite3
import time
from datetime import datetime

class Action(Enum):
    Measure = auto()
    Preprocess = auto()

@dataclass
class TKI_step:
    channel: int
    action: Action

class Registrator:
    def __init__(self, channels_params: list[ChannelParam], tki_steps: list[TKI_step], plant: Plant):
        self.frames = []
        self.last_frame = []
        self.registrating = False
    
        self.measure_status = MeasureError.NoError
        self.fail_info = None
        def process_measure_error(error: MeasureError, info: Any):
            self.measure_status = error
            self.fail_info = info

        # Создаём объекты каналов
        self.channels: dict[int, Channel] = dict()
        self.channels_db_names: list[str] = []
        self.channels_display_names: list[str] = []
        for param in channels_params:
            channel = Channel(param.number, plant, param.preprocessing, param.additional_params)
            channel.connect_control_fail_callbacks(process_measure_error)
            self.channels[param.number] = channel

            if param.preprocessing != Preprocessing.StableControl:
                # Добавляем названия столбцов для значений, которые улетят в БД
                self.channels_db_names += param.columns_in_db
                # Добавляем названия столбцов для отображения в программе
                self.channels_display_names += channel.display_names

        self.tki_steps = tki_steps
        self.startdate = None

    def measure_frame(self):
        self.measure_status = MeasureError.NoError
        self.fail_info = None

        if self.startdate is None:
            self.startdate = datetime.now().isoformat()

        for tki_step in self.tki_steps:
            channel_num = tki_step.channel
            
            # Выполнение операции
            if tki_step.action == Action.Measure:
                self.channels[channel_num].measure()
                time.sleep(0.001)

            if tki_step.action == Action.Preprocess:
                self.channels[channel_num].preproccess()
                time.sleep(0.001)
        
            # Ошибка стабильности
            if self.measure_status == MeasureError.StabilityControl:
                break
            
        if self.measure_status == MeasureError.StabilityControl:
            self.measure_frame()
        else:
            self.save_frame()
    

    def save_frame(self):
        frame_number = len(self.frames) + 1
        current_datetime = datetime.now().isoformat()
        frame = [frame_number, current_datetime]

        for channel in self.channels.values():
            if channel.preproccess_type == Preprocessing.StableControl:
                # Значения контроля стабильности не летят в БД и не сохраняются
                continue

            channel_measurement = channel.current_measurement
            if len(channel_measurement) != channel.output_size:
                frame += [None, ] * channel.output_size
            else:
                frame += channel_measurement
        
        self.last_frame = tuple(frame)
        self.frames.append(self.last_frame)

    @contextmanager
    def get_db_connection(self, db_path: str):
        conn = sqlite3.connect(db_path)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            print(e)
        finally:
            conn.close()

    def save_to_db(self, db_path: str, operator_fio: str = 'Ивнов Иван', description: str = 'Описания не задано'):
        columns_names = self.channels_db_names
        rows = self.frames

        with self.get_db_connection(db_path) as conn:
            TABLE_NAME = 'Measurements'

            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Exp_info (
                    EXP_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    OPERATOR_FIO TEXT NOT NULL,
                    DESCRIPTION TEXT,
                    EXP_DATE TEXT,
                    CREATE_DATE TEXT
                )
            ''')

            # Создание таблицы
            table_columns_list = [ f"{name} REAL NULL" for name in columns_names ]
            table_columns = ', '.join(table_columns_list)
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    EXP_ID INTEGER,
                    FRAME_NUM INT,
                    FRAME_TIME TEXT,
                    {table_columns},
                    FOREIGN KEY (EXP_ID) REFERENCES Exp_info(EXP_ID) ON DELETE CASCADE
                )
            ''')

            # Включаем поддержку внешних ключей
            cursor.execute('PRAGMA foreign_keys = ON')
            
            cursor.execute('''
                INSERT INTO Exp_info (OPERATOR_FIO, DESCRIPTION, EXP_DATE, CREATE_DATE)
                VALUES (?, ?, ?, ?)
            ''', (operator_fio, description, self.startdate, datetime.now().isoformat()))

            experiment_id = cursor.lastrowid
            print(f"ID эксперимента: {experiment_id}")

            rows_with_exp_id = [ [experiment_id, ] + list(row) for row in rows ]
            # Вставка данных
            placeholders = ', '.join('?' * (3 + len(columns_names)))
            sql = f'INSERT INTO {TABLE_NAME} (EXP_ID, FRAME_NUM, FRAME_TIME, {', '.join(columns_names)}) VALUES ({placeholders})'
            print(sql)
            
            cursor.executemany(
                sql,
                rows_with_exp_id
            )

    def start_registration(self):
        self.registrating = True

    def stop_registration(self):
        self.registrating = False