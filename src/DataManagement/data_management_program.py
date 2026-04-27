"""
Программа управления данными (П2)
Data Management Program for experiment data viewing, filtering, sorting and export
"""

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import csv
from pathlib import Path
import re


class DataManagementProgram:
    """Основной класс программы управления данными"""
    
    def __init__(self, db_path: str = "measurements.db"):
        """
        Инициализация программы
        
        Args:
            db_path: путь к файлу базы данных SQLite
        """
        self.db_path = db_path
        self.current_exp_id = None
        self.current_operator = None
        self.current_exp_date = None
        self.current_data = []  # Хранит текущие отображаемые данные
        self.current_columns = []  # Хранит имена столбцов
        self.original_data = []  # Хранит оригинальные данные (для сброса фильтра)
        self.original_columns = []  # Хранит оригинальные столбцы
        self.last_sort_column = None  # Последний столбец для сортировки
        self.last_sort_reverse = False  # Направление сортировки
        
        self.root = tk.Tk()
        self.root.title("Управление данными - Программа П2")
        self.root.geometry("1400x800")
        
        # Настройка минимальных размеров окна
        self.root.minsize(1000, 600)
        
        self._setup_ui()
        self._load_experiments_list()
        
        # Привязываем событие изменения размера окна
        self.root.bind('<Configure>', self._on_window_resize)
        
    def _setup_ui(self):
        """Настройка пользовательского интерфейса"""
        
        # Основной контейнер с возможностью изменения размера
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Верхняя панель (фиксированная часть)
        self.top_container = ttk.Frame(self.main_paned)
        self.main_paned.add(self.top_container, weight=0)
        
        # Панель выбора эксперимента
        self.top_frame = ttk.LabelFrame(self.top_container, text="Выбор эксперимента", padding=10)
        self.top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Центрируем содержимое панели выбора эксперимента
        top_inner_frame = ttk.Frame(self.top_frame)
        top_inner_frame.pack(anchor=tk.CENTER)
        
        # Выбор оператора
        ttk.Label(top_inner_frame, text="Оператор:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.operator_var = tk.StringVar()
        self.operator_combo = ttk.Combobox(top_inner_frame, textvariable=self.operator_var, width=30)
        self.operator_combo.grid(row=0, column=1, padx=5)
        self.operator_combo.bind('<<ComboboxSelected>>', self._on_operator_selected)
        
        # Выбор эксперимента
        ttk.Label(top_inner_frame, text="Эксперимент:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.exp_var = tk.StringVar()
        self.exp_combo = ttk.Combobox(top_inner_frame, textvariable=self.exp_var, width=50)
        self.exp_combo.grid(row=0, column=3, padx=5)
        self.exp_combo.bind('<<ComboboxSelected>>', self._on_experiment_selected)
        
        # Кнопка обновления
        self.refresh_btn = ttk.Button(top_inner_frame, text="Обновить список", command=self._load_experiments_list)
        self.refresh_btn.grid(row=0, column=4, padx=10)
        
        # Панель управления (средние значения и фильтрация)
        self.control_frame = ttk.Frame(self.top_container)
        self.control_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Настройка весов для равномерного растягивания
        self.control_frame.grid_columnconfigure(0, weight=3)  # Средние значения
        self.control_frame.grid_columnconfigure(1, weight=1)  # Фильтрация
        self.control_frame.grid_rowconfigure(0, weight=1)
        
        # Левая часть - средние значения (растягивается)
        self.avg_frame = ttk.LabelFrame(self.control_frame, text="Средние значения каналов", padding=10)
        self.avg_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # Создаем внутренний фрейм для сетки 2x12
        avg_inner_frame = ttk.Frame(self.avg_frame)
        avg_inner_frame.pack(expand=True, fill=tk.BOTH)
        
        # Создаем 12 колонок для каналов
        self.avg_labels = {}
        self.avg_values = {}
        
        # Создаем 12 колонок для каналов
        for i in range(12):
            # Создаем фрейм для каждого канала
            channel_frame = ttk.Frame(avg_inner_frame)
            channel_frame.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            
            # Название канала сверху
            channel_label = ttk.Label(channel_frame, text=f"Канал {i+1}", font=('Arial', 9, 'bold'), anchor='center')
            channel_label.pack(fill=tk.X, pady=(0, 2))
            
            # Значение канала снизу
            self.avg_values[f"channel_{i+1}"] = tk.StringVar(value="—")
            avg_label = ttk.Label(channel_frame, textvariable=self.avg_values[f"channel_{i+1}"], 
                                  font=('Arial', 9), anchor='center', relief=tk.SUNKEN, padding=2)
            avg_label.pack(fill=tk.X)
            self.avg_labels[f"channel_{i+1}"] = avg_label
            
            # Настройка весов для равномерного распределения
            avg_inner_frame.grid_columnconfigure(i, weight=1)
        
        # Правая часть - фильтрация (без центрирования, как было ранее)
        self.filter_frame = ttk.LabelFrame(self.control_frame, text="Фильтрация данных", padding=10)
        self.filter_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Выбор канала для фильтрации
        ttk.Label(self.filter_frame, text="Канал:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.filter_channel_var = tk.StringVar()
        self.filter_channel_combo = ttk.Combobox(self.filter_frame, textvariable=self.filter_channel_var, 
                                                  width=25, state="readonly")
        self.filter_channel_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # Диапазон значений
        ttk.Label(self.filter_frame, text="Диапазон:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        filter_range_frame = ttk.Frame(self.filter_frame)
        filter_range_frame.grid(row=1, column=1, padx=5, pady=5)
        
        # Валидация ввода чисел
        vcmd = (self.root.register(self._validate_number_input), '%P')
        
        self.filter_min_var = tk.StringVar()
        self.filter_min_entry = ttk.Entry(filter_range_frame, textvariable=self.filter_min_var, 
                                           width=12, validate='key', validatecommand=vcmd)
        self.filter_min_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(filter_range_frame, text="до").pack(side=tk.LEFT, padx=5)
        
        self.filter_max_var = tk.StringVar()
        self.filter_max_entry = ttk.Entry(filter_range_frame, textvariable=self.filter_max_var, 
                                           width=12, validate='key', validatecommand=vcmd)
        self.filter_max_entry.pack(side=tk.LEFT, padx=2)
        
        # Кнопки фильтрации
        filter_buttons_frame = ttk.Frame(self.filter_frame)
        filter_buttons_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        self.filter_btn = ttk.Button(filter_buttons_frame, text="Применить фильтр", command=self._apply_filter, width=18)
        self.filter_btn.pack(side=tk.LEFT, padx=5)
        
        self.reset_filter_btn = ttk.Button(filter_buttons_frame, text="Сбросить фильтр", command=self._reset_filter, width=18)
        self.reset_filter_btn.pack(side=tk.LEFT, padx=5)
        
        # Таблица данных (растягивается)
        self.table_container = ttk.Frame(self.main_paned)
        self.main_paned.add(self.table_container, weight=1)
        
        # Создаем Treeview с прокруткой
        self.tree_frame = ttk.Frame(self.table_container)
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Настройка прокрутки
        self.tree = ttk.Treeview(self.tree_frame, show='headings')
        self.vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        self.vsb.grid(row=0, column=1, sticky='ns')
        self.hsb.grid(row=1, column=0, sticky='ew')
        
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        
        # Привязываем событие клика по заголовку
        self.tree.bind('<ButtonRelease-1>', self._on_tree_click)
        
        # Нижняя панель с кнопкой экспорта (центрирование)
        self.bottom_frame = ttk.Frame(self.table_container)
        self.bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Центрируем кнопку
        bottom_inner_frame = ttk.Frame(self.bottom_frame)
        bottom_inner_frame.pack(anchor=tk.CENTER)
        
        self.export_btn = ttk.Button(bottom_inner_frame, text="Экспортировать в CSV", command=self._export_to_csv, width=22)
        self.export_btn.pack(side=tk.LEFT, padx=10)
        
    def _on_window_resize(self, event=None):
        """Обработчик изменения размера окна - перерастягиваем колонки таблицы"""
        # Проверяем, что событие относится к главному окну и таблица существует
        if event.widget == self.root and hasattr(self, 'tree') and self.current_columns:
            self.root.update_idletasks()
            self._resize_tree_columns()
    
    def _resize_tree_columns(self):
        """Растянуть колонки таблицы на всю доступную ширину"""
        if not self.current_columns:
            return
            
        total_width = self.tree.winfo_width()
        if total_width > 100:
            # Считаем сумму фиксированных ширин для первых N-1 колонок
            fixed_width = 0
            for col in self.current_columns[:-1]:  # Все кроме последнего
                if col == 'Время кадра':
                    fixed_width += 180
                elif col == 'Номер кадра':
                    fixed_width += 100
                else:
                    fixed_width += 120
            
            # Последнюю колонку растягиваем на оставшееся место
            last_col = self.current_columns[-1]
            remaining_width = max(100, total_width - fixed_width - 25)  # 25px на скролл
            self.tree.column(last_col, width=remaining_width, minwidth=100)
        
    def _validate_number_input(self, value):
        """Валидация ввода чисел (разрешены цифры, минус и точка)"""
        if value == "" or value == "-":
            return True
        # Разрешаем цифры, минус в начале и точку
        pattern = r'^-?\d*\.?\d*$'
        return bool(re.match(pattern, value))
    
    def _format_datetime(self, datetime_str):
        """Форматирование даты и времени для отображения"""
        if not datetime_str:
            return "—"
        try:
            # Пробуем разные форматы
            if 'T' in datetime_str:
                # ISO формат с T
                dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                return dt.strftime("%d.%m.%Y %H:%M:%S")
            else:
                # Другие форматы
                return datetime_str.replace('T', ' ').replace('Z', '')
        except:
            return datetime_str
    
    def _format_number(self, value):
        """Форматирование числа (до 3 значащих цифр)"""
        if value is None or value == '—':
            return "—"
        try:
            num = float(value)
            # Проверяем, является ли число целым
            if abs(num - round(num)) < 0.0001:
                return str(int(round(num)))
            else:
                # Форматируем до 3 значащих цифр
                if abs(num) >= 100:
                    return f"{num:.1f}"
                elif abs(num) >= 10:
                    return f"{num:.2f}"
                else:
                    return f"{num:.3f}"
        except (ValueError, TypeError):
            return str(value)
    
    def _get_db_connection(self):
        """Получить соединение с БД"""
        return sqlite3.connect(self.db_path)
    
    def _try_convert_to_float(self, value):
        """Попытка преобразовать значение в число"""
        if value is None or value == 'NULL' or value == '':
            return None
        try:
            # Если это строка, пробуем преобразовать
            if isinstance(value, str):
                # Заменяем запятую на точку
                value = value.replace(',', '.')
                return float(value)
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _load_experiments_list(self):
        """Загрузить список всех экспериментов из БД"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT EXP_ID, OPERATOR_FIO, EXP_DATE, END_DATE 
                    FROM Exp_info 
                    ORDER BY EXP_DATE DESC
                """)
                experiments = cursor.fetchall()
                
                if not experiments:
                    self.operator_combo['values'] = []
                    self.exp_combo['values'] = []
                    return
                
                # Группируем по операторам
                operators = {}
                for exp_id, operator_fio, exp_date, end_date in experiments:
                    if operator_fio not in operators:
                        operators[operator_fio] = []
                    # Форматируем дату для отображения
                    exp_date_str = self._format_datetime(exp_date) if exp_date else "дата не указана"
                    end_date_str = self._format_datetime(end_date) if end_date else "активен"
                    exp_str = f"ID:{exp_id} | {exp_date_str} | {end_date_str}"
                    operators[operator_fio].append((exp_id, exp_str))
                
                # Сохраняем данные
                self.operators_data = operators
                operator_list = list(operators.keys())
                self.operator_combo['values'] = operator_list
                
                if operator_list:
                    self.operator_combo.set(operator_list[0])
                    self._on_operator_selected()
                    
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка БД", f"Не удалось загрузить список экспериментов: {e}")
    
    def _on_operator_selected(self, event=None):
        """При выборе оператора - обновить список его экспериментов"""
        # Очищаем поля фильтра
        self.filter_min_var.set("")
        self.filter_max_var.set("")
        
        operator = self.operator_var.get()
        if operator and operator in self.operators_data:
            experiments = [exp_str for exp_id, exp_str in self.operators_data[operator]]
            self.exp_combo['values'] = experiments
            if experiments:
                self.exp_combo.set(experiments[0])
                self._on_experiment_selected()

    def _on_experiment_selected(self, event=None):
        """При выборе эксперимента - загрузить данные"""
        # Очищаем поля фильтра
        self.filter_min_var.set("")
        self.filter_max_var.set("")
        
        exp_str = self.exp_var.get()
        
        if not exp_str:
            return
        
        # Извлекаем EXP_ID из строки
        try:
            exp_id = int(exp_str.split('|')[0].replace('ID:', '').strip())
            self.current_exp_id = exp_id
            self._load_experiment_data(exp_id)
        except (ValueError, IndexError) as e:
            messagebox.showerror("Ошибка", f"Не удалось определить ID эксперимента: {e}")
    
    def _load_experiment_data(self, exp_id):
        """Загрузить данные эксперимента из БД"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем информацию об эксперименте
                cursor.execute("""
                    SELECT OPERATOR_FIO, EXP_DATE, END_DATE 
                    FROM Exp_info 
                    WHERE EXP_ID = ?
                """, (exp_id,))
                exp_info = cursor.fetchone()
                
                if exp_info:
                    self.current_operator, exp_date, end_date = exp_info
                    self.current_exp_date = self._format_datetime(exp_date)
                    self.root.title(f"Управление данными - Эксперимент #{exp_id} | Оператор: {self.current_operator} | Дата: {self.current_exp_date}")
                
                # Получаем все столбцы таблицы Measurements
                cursor.execute("PRAGMA table_info(Measurements)")
                all_columns = cursor.fetchall()
                
                if not all_columns:
                    messagebox.showwarning("Предупреждение", "Таблица Measurements не найдена в БД")
                    return
                
                # Определяем динамические столбцы
                exclude_columns = {'id', 'EXP_ID', 'FRAME_NUM', 'FRAME_TIME'}
                data_columns = [col[1] for col in all_columns if col[1] not in exclude_columns]
                
                if not data_columns:
                    messagebox.showwarning("Предупреждение", "В таблице Measurements нет столбцов с данными")
                    return
                
                # Загружаем данные
                columns_str = ', '.join(data_columns)
                cursor.execute(f"""
                    SELECT FRAME_NUM, FRAME_TIME, {columns_str}
                    FROM Measurements 
                    WHERE EXP_ID = ?
                    ORDER BY FRAME_NUM
                """, (exp_id,))
                
                rows = cursor.fetchall()
                
                if not rows:
                    messagebox.showinfo("Информация", f"В эксперименте #{exp_id} нет данных")
                    self.current_data = []
                    self.current_columns = ['Номер кадра', 'Время кадра'] + data_columns
                    self.original_data = []
                    self._update_table()
                    return
                
                # Преобразуем данные
                converted_rows = []
                for row in rows:
                    converted_row = []
                    for i, value in enumerate(row):
                        if i == 0:  # FRAME_NUM
                            converted_row.append(value)
                        elif i == 1:  # FRAME_TIME
                            converted_row.append(self._format_datetime(value))
                        else:
                            converted_row.append(self._try_convert_to_float(value))
                    converted_rows.append(converted_row)
                
                # Сохраняем данные
                self.current_columns = ['Номер кадра', 'Время кадра'] + data_columns
                self.current_data = converted_rows
                self.original_data = [row[:] for row in converted_rows]
                
                # Рассчитываем средние значения
                self._calculate_averages(data_columns, converted_rows)
                
                # Обновляем таблицу
                self._update_table()
                
                # Обновляем список каналов для фильтрации
                self.filter_channel_combo['values'] = data_columns
                if data_columns:
                    self.filter_channel_combo.set(data_columns[0])
                
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка БД", f"Не удалось загрузить данные: {e}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка: {e}")
    
    def _calculate_averages(self, data_columns, rows):
        """Рассчитать и отобразить средние значения по каналам"""
        # Сброс значений
        for key in self.avg_values:
            self.avg_values[key].set("—")
        
        if not rows:
            return
        
        # Рассчитываем средние для каждого канала (максимум 12)
        for i in range(min(len(data_columns), 12)):
            values = []
            for row in rows:
                if i + 2 < len(row):  # Проверяем границы
                    val = row[i + 2]  # +2 because first two columns are FRAME_NUM and FRAME_TIME
                    if val is not None and isinstance(val, (int, float)):
                        values.append(val)
            
            if values:
                avg = sum(values) / len(values)
                # Форматируем число
                if abs(avg - round(avg)) < 0.0001:
                    avg_str = str(int(round(avg)))
                else:
                    avg_str = f"{avg:.3f}"
                
                channel_key = list(self.avg_values.keys())[i]
                self.avg_values[channel_key].set(avg_str)
    
    def _update_table(self):
        """Обновить таблицу с текущими данными"""
        # Очищаем текущие данные
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not self.current_data or not self.current_columns:
            return
        
        # Настраиваем колонки
        self.tree['columns'] = self.current_columns
        for col in self.current_columns:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_by_column(c))
            # Устанавливаем ширину колонок
            if col == 'Время кадра':
                self.tree.column(col, width=180, minwidth=150)
            elif col == 'Номер кадра':
                self.tree.column(col, width=100, minwidth=80)
            else:
                self.tree.column(col, width=120, minwidth=100)
        
        # Вставляем данные
        for row in self.current_data:
            # Форматируем значения для отображения
            str_row = []
            for i, val in enumerate(row):
                if i == 0:  # Номер кадра
                    str_row.append(str(val))
                elif i == 1:  # Время кадра
                    str_row.append(val)
                else:
                    str_row.append(self._format_number(val))
            self.tree.insert('', tk.END, values=str_row)
        
        # Растягиваем колонки после обновления данных
        self.root.update_idletasks()
        self._resize_tree_columns()
    
    def _sort_by_column(self, col):
        """Сортировка по колонке (вызывается при клике на заголовок)"""
        # Определяем индекс колонки
        col_index = self.current_columns.index(col)
        
        # Определяем направление сортировки
        if self.last_sort_column == col:
            self.last_sort_reverse = not self.last_sort_reverse
        else:
            self.last_sort_column = col
            self.last_sort_reverse = False
        
        # Сортируем данные
        def get_sort_key(row):
            val = row[col_index]
            if val is None or val == '—':
                return float('inf') if self.last_sort_reverse else float('-inf')
            try:
                # Пробуем преобразовать в число
                if isinstance(val, str):
                    # Убираем пробелы и заменяем запятую
                    val_clean = val.replace(' ', '').replace(',', '.')
                    return float(val_clean)
                return float(val)
            except (ValueError, TypeError):
                return str(val)
        
        self.current_data.sort(key=get_sort_key, reverse=self.last_sort_reverse)
        self._update_table()
    
    def _on_tree_click(self, event):
        """Обработка клика по заголовку таблицы для сортировки (альтернативный метод)"""
        region = self.tree.identify_region(event.x, event.y)
        if region == "heading":
            column = self.tree.identify_column(event.x)
            if column:
                col_index = int(column.replace('#', '')) - 1
                if col_index < len(self.current_columns):
                    col_name = self.current_columns[col_index]
                    self._sort_by_column(col_name)
    
    def _apply_filter(self):
        """Применить фильтр к данным"""
        channel = self.filter_channel_var.get()
        min_val = self.filter_min_var.get().strip()
        max_val = self.filter_max_var.get().strip()
        
        if not channel:
            messagebox.showwarning("Предупреждение", "Выберите канал для фильтрации")
            return
        
        if not min_val and not max_val:
            messagebox.showwarning("Предупреждение", "Укажите хотя бы одну границу диапазона")
            return
        
        if channel not in self.current_columns:
            messagebox.showwarning("Предупреждение", "Выбранный канал не найден в данных")
            return
        
        col_index = self.current_columns.index(channel)
        filtered_data = []
        
        # Используем оригинальные данные для фильтрации
        source_data = self.original_data if self.original_data else self.current_data
        
        # Преобразуем границы в числа
        min_float = None
        max_float = None
        
        try:
            if min_val:
                min_float = float(min_val.replace(',', '.'))
            if max_val:
                max_float = float(max_val.replace(',', '.'))
        except ValueError:
            messagebox.showerror("Ошибка", "Границы диапазона должны быть числами")
            return
        
        for row in source_data:
            value = row[col_index]
            
            # Пропускаем None значения
            if value is None or value == '—':
                continue
            
            # Преобразуем значение в число
            try:
                if isinstance(value, str):
                    float_val = float(value.replace(',', '.'))
                else:
                    float_val = float(value)
            except (ValueError, TypeError):
                continue
            
            # Проверяем условия
            min_ok = True
            max_ok = True
            
            if min_float is not None:
                min_ok = float_val >= min_float
            if max_float is not None:
                max_ok = float_val <= max_float
            
            if min_ok and max_ok:
                filtered_data.append(row)
        
        if filtered_data:
            self.current_data = filtered_data
            self._update_table()
            messagebox.showinfo("Информация", f"Найдено {len(filtered_data)} записей из {len(self.original_data)}")
        else:
            messagebox.showinfo("Информация", "По заданному фильтру данные не найдены")
    
    def _reset_filter(self):
        """Сбросить фильтр и показать все данные"""
        self.filter_min_var.set("")
        self.filter_max_var.set("")
        
        if self.original_data:
            self.current_data = [row[:] for row in self.original_data]
            self.last_sort_column = None
            self.last_sort_reverse = False
            self._update_table()
    
    def _sanitize_filename(self, filename):
        """Очистка имени файла от недопустимых символов"""
        # Заменяем недопустимые символы на подчеркивания
        return re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    def _export_to_csv(self):
        """Экспортировать текущие данные в CSV файл"""
        if not self.current_data or not self.current_columns:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
            return
        
        # Формируем имя файла: Фамилия_Время_эксперимент
        # Получаем фамилию из ФИО (первое слово)
        operator_surname = self.current_operator.split()[0] if self.current_operator else "Unknown"
        
        # Текущее время для имени файла
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Формируем имя файла
        filename = f"{operator_surname}_{current_time}_exp{self.current_exp_id}"
        filename = self._sanitize_filename(filename)
        
        # Выбираем файл для сохранения
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=filename
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                
                # Записываем заголовки
                writer.writerow(self.current_columns)
                
                # Записываем данные
                for row in self.current_data:
                    writer.writerow(row)
            
            messagebox.showinfo("Успех", f"Данные успешно экспортированы в файл:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", f"Не удалось сохранить файл: {e}")
    
    def run(self):
        """Запустить программу"""
        self.root.mainloop()


def main():
    """Точка входа"""
    # Путь к файлу БД
    db_path = Path(__file__).parent.parent / "measurements.db"
    
    # Проверяем существование БД
    if not Path(db_path).exists():
        print(f"Внимание: База данных '{db_path}' не найдена. Убедитесь, что П1 создала БД.")
        response = messagebox.askyesno("Предупреждение", 
                                       f"База данных '{db_path}' не найдена.\n"
                                       "Вы хотите продолжить (будет создана новая БД)?")
        if not response:
            return
    
    # Создаем и запускаем программу
    app = DataManagementProgram(db_path)
    app.run()


if __name__ == "__main__":
    main()