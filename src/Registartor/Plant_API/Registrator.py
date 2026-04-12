from .Channel import Channel, ChannelParam
from .Plant import Plant
from dataclasses import dataclass
from enum import Enum, auto
from contextlib import contextmanager
import sqlite3


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
            self.channels[param.number] = Channel(param.number, plant, param.preprocessing)
            # Добавляем названия столбцов для значений, которые улетят в БД
            for column_in_db in param.columns_in_db:
                self.channels_names.append(column_in_db)

        self.tki_steps = tki_steps

    def measure(self):
        for tki_step in self.tki_steps:
            channel_num = tki_step.channel
            
            if tki_step.action == Action.Measure:
                self.channels[channel_num].measure()
                continue

            if tki_step.action == Action.Preprocess:
                self.channels[channel_num].preproccess()
                continue
        
        self.save_frame()
        
    def save_frame(self):
        frame = []
        for channel in self.channels.values():
            channel_measurement = channel.current_measurement 
            frame += channel_measurement
        
        self.last_frame = tuple(frame)
        self.frames.append(self.last_frame)

    @contextmanager
    def get_db_connection(self, db_path: str):
        conn = sqlite3.connect(db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save_to_db(self, db_path: str):
        columns_names = self.channels_names.values()
        rows = self.frames

        with self.get_db_connection(db_path) as conn:
            TABLE_NAME = 'Measurements'

            cursor = conn.cursor()

            # Создание таблицы
            table_columns_list = [ f"{name} REAL NULL" for name in columns_names ]
            table_columns = ', '.join(table_columns_list)
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    {table_columns}
                )
            ''')
            
            # Вставка данных
            placeholders = ', '.join('?' * len(columns_names))
            cursor.executemany(
                f'INSERT INTO {TABLE_NAME} ({columns_names}) VALUES ({placeholders})',
                rows
            )

