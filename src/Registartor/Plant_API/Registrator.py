from .Channel import Channel, ChannelParam
from .Plant import Plant
from dataclasses import dataclass
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
    
        # Создаём объекты каналов
        self.channels: dict[int, Channel] = dict()
        self.channels_names: list[str] = []
        for param in channels_params:
            self.channels[param.number] = Channel(param.number, plant, param.preprocessing, param.additional_params)
            # Добавляем названия столбцов для значений, которые улетят в БД
            for column_in_db in param.columns_in_db:
                self.channels_names.append(column_in_db)

        self.tki_steps = tki_steps
        self.startdate = None

    def measure_frame(self):
        if self.startdate is None:
            self.startdate = datetime.now().isoformat()

        for tki_step in self.tki_steps:
            channel_num = tki_step.channel
            
            if tki_step.action == Action.Measure:
                self.channels[channel_num].measure()
                time.sleep(0.001)
                continue

            if tki_step.action == Action.Preprocess:
                self.channels[channel_num].preproccess()
                time.sleep(0.001)
                continue
        
        self.save_frame()
        
    def save_frame(self):
        frame_number = len(self.frames) + 1
        current_datetime = datetime.now().isoformat()
        frame = [frame_number, current_datetime]

        for channel in self.channels.values():
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

    def save_to_db(self, db_path: str, operator_fio: str = 'Ивнов Иван'):
        columns_names = self.channels_names
        rows = self.frames

        with self.get_db_connection(db_path) as conn:
            TABLE_NAME = 'Measurements'

            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Exp_info (
                    EXP_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    OPERATOR_FIO TEXT NOT NULL,
                    EXP_DATE TEXT,
                    END_DATE TEXT DEFAULT CURRENT_TIMESTAMP
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
                INSERT INTO Exp_info (OPERATOR_FIO, EXP_DATE)
                VALUES (?, ?)
            ''', (operator_fio, self.startdate))

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

    