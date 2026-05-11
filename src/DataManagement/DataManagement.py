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


class DataManagement:
    """Основной класс программы управления данными"""
    
    def __init__(self, db_path: str = None, parent = None, tab_name: str = ''):
        """
        Инициализация программы
        
        Args:
            db_path: путь к файлу базы данных SQLite
        """
        # Если путь не указан, используем путь к БД в корневой папке tpposu-develop
        if db_path is None:
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent
            db_path = str(project_root / 'measurements.db')
        
        self.db_path = db_path
        self.parent = parent
        self.tab_name = tab_name

        self.current_exp_id = None
        self.current_operator = None
        self.current_exp_date = None
        self.current_description = None
        self.current_data = []
        self.current_columns = []
        self.display_columns = []
        self.original_data = []
        self.last_sort_column = None
        self.last_sort_reverse = False
        self.filter_channel_map = {}

        self.main_frame = ttk.Frame(parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.root = self._get_root_window()
        self.title = 'Работа с данными'
        
        self._setup_ui()
        self._load_experiments_list()
        
        self._resizing = False
        self._resize_after_id = None

    def _get_root_window(self):
        widget = self.main_frame
        while widget:
            if isinstance(widget, tk.Tk):
                return widget
            widget = widget.master
        return None

    def _get_russian_column_name(self, col_name):
        """Преобразовать английское название столбца в русское (как в регистраторе)"""
        russian_names = {
            'FRAME_NUM': 'Кадр',
            'FRAME_TIME': 'Время замера',
            'CH1_RAW': 'Кан-1',
            'CH2_RAW': 'Кан-2',
            'CH3_RAW': 'Кан-3',
            'CH4_RAW': 'Кан-4',
            'CH5_NORM': 'Кан-5-СТД',
            'CH6_MEAN': 'Кан-6-СР',
            'CH6_DISP': 'Кан-6-ДИСП',
            'CH9_VAL': 'Кан-9',
            'CH16_RAW': 'Кан-16',
            'CH46_RAW': 'Кан-46',
            'CH66_FUNC': 'Кан-66-ФУНК',
            'CH76_VAL': 'Кан-76',
        }
        return russian_names.get(col_name, col_name)

    def _setup_ui(self):
        """Настройка пользовательского интерфейса"""
        
        self.main_paned = ttk.PanedWindow(self.main_frame, orient=tk.VERTICAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        self.top_container = ttk.Frame(self.main_paned)
        self.main_paned.add(self.top_container, weight=0)
        
        # Панель выбора эксперимента
        self.top_frame = ttk.LabelFrame(self.top_container, text="Выбор эксперимента", padding=10)
        self.top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        top_inner_frame = ttk.Frame(self.top_frame)
        top_inner_frame.pack(anchor=tk.CENTER)
        
        ttk.Label(top_inner_frame, text="Оператор:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.operator_var = tk.StringVar()
        self.operator_combo = ttk.Combobox(top_inner_frame, textvariable=self.operator_var, width=30)
        self.operator_combo.grid(row=0, column=1, padx=5)
        self.operator_combo.bind('<<ComboboxSelected>>', self._on_operator_selected)
        
        ttk.Label(top_inner_frame, text="Эксперимент:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.exp_var = tk.StringVar()
        self.exp_combo = ttk.Combobox(top_inner_frame, textvariable=self.exp_var, width=60)
        self.exp_combo.grid(row=0, column=3, padx=5)
        self.exp_combo.bind('<<ComboboxSelected>>', self._on_experiment_selected)
        
        self.refresh_btn = ttk.Button(top_inner_frame, text="Обновить список", command=self._load_experiments_list)
        self.refresh_btn.grid(row=0, column=4, padx=10)
        
        # Панель фильтрации данных
        self.filter_frame = ttk.LabelFrame(self.top_container, text="Фильтрация данных", padding=10)
        self.filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        filter_row = ttk.Frame(self.filter_frame)
        filter_row.pack(fill=tk.X, pady=5)
        
        ttk.Label(filter_row, text="Канал:").pack(side=tk.LEFT, padx=5)
        self.filter_channel_var = tk.StringVar()
        self.filter_channel_combo = ttk.Combobox(filter_row, textvariable=self.filter_channel_var, 
                                                  width=25, state="readonly")
        self.filter_channel_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(filter_row, text="Диапазон:").pack(side=tk.LEFT, padx=(10, 2))
        
        vcmd = (self.root.register(self._validate_number_input), '%P')
        
        self.filter_min_var = tk.StringVar()
        self.filter_min_entry = ttk.Entry(filter_row, textvariable=self.filter_min_var, 
                                           width=12, validate='key', validatecommand=vcmd)
        self.filter_min_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(filter_row, text="до").pack(side=tk.LEFT, padx=2)
        
        self.filter_max_var = tk.StringVar()
        self.filter_max_entry = ttk.Entry(filter_row, textvariable=self.filter_max_var, 
                                           width=12, validate='key', validatecommand=vcmd)
        self.filter_max_entry.pack(side=tk.LEFT, padx=2)
        
        filter_buttons_frame = ttk.Frame(self.filter_frame)
        filter_buttons_frame.pack(fill=tk.X, pady=5)
        
        self.filter_btn = ttk.Button(filter_buttons_frame, text="Применить фильтр", command=self._apply_filter, width=18)
        self.filter_btn.pack(side=tk.LEFT, padx=5)
        
        self.reset_filter_btn = ttk.Button(filter_buttons_frame, text="Сбросить фильтр", command=self._reset_filter, width=18)
        self.reset_filter_btn.pack(side=tk.LEFT, padx=5)
        
        # Контейнер для таблиц
        self.tables_container = ttk.Frame(self.main_paned)
        self.main_paned.add(self.tables_container, weight=1)
        
        # Основная таблица данных
        self.tree_frame = ttk.Frame(self.tables_container)
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 0))
        
        self.tree = ttk.Treeview(self.tree_frame, show='headings')
        self.vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        self.vsb.grid(row=0, column=1, sticky='ns')
        self.hsb.grid(row=1, column=0, sticky='ew')
        
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        
        self.tree.bind('<ButtonRelease-1>', self._on_tree_click)
        self.tree.bind('<Configure>', self._on_tree_column_resize)
        
        # Нижняя таблица для средних значений
        self.avg_bottom_frame = ttk.Frame(self.tables_container)
        self.avg_bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        self.avg_tree = ttk.Treeview(self.avg_bottom_frame, show='tree', height=1)
        self.avg_tree.pack(fill=tk.X)
        self.avg_tree.tag_configure('avg_row', background='#e0e0e0')
        
        # Нижняя панель с кнопкой экспорта
        self.bottom_frame = ttk.Frame(self.tables_container)
        self.bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        
        bottom_inner_frame = ttk.Frame(self.bottom_frame)
        bottom_inner_frame.pack(anchor=tk.CENTER)
        
        self.export_btn = ttk.Button(bottom_inner_frame, text="Экспортировать в CSV", command=self._export_to_csv, width=22)
        self.export_btn.pack(side=tk.LEFT, padx=10)

    def _on_tree_column_resize(self, event):
        if hasattr(self, 'current_columns') and self.current_columns:
            self.root.after(100, self._sync_avg_table)

    def _calculate_averages_list(self):
        if not self.current_data or not self.current_columns:
            return []
        
        averages = []
        for col_index, col_name in enumerate(self.current_columns):
            if col_name in ['FRAME_NUM', 'FRAME_TIME']:
                continue
            
            values = []
            for row in self.current_data:
                if col_index < len(row):
                    val = row[col_index]
                    if val is not None and isinstance(val, (int, float)):
                        values.append(val)
            
            if values:
                avg = sum(values) / len(values)
                if abs(avg - round(avg)) < 0.0001:
                    avg_str = str(int(round(avg)))
                else:
                    avg_str = f"{avg:.3f}"
            else:
                avg_str = "—"
            
            averages.append(avg_str)
        
        return averages

    def _sync_avg_table(self):
        if not self.current_columns:
            return
        
        main_cols_count = len(self.current_columns)
        avg_cols_count = main_cols_count - 1
        
        self.avg_tree['columns'] = list(range(avg_cols_count))
        
        col0_width = self.tree.column('FRAME_NUM', 'width') + self.tree.column('FRAME_TIME', 'width')
        self.avg_tree.column(0, width=col0_width, minwidth=col0_width)
        
        for i, col_name in enumerate(self.current_columns[2:], start=1):
            width = self.tree.column(col_name, 'width')
            self.avg_tree.column(i, width=width, minwidth=width)
        
        for item in self.avg_tree.get_children():
            self.avg_tree.delete(item)
        
        avg_values = self._calculate_averages_list()
        avg_row = ["Средние значения"] + avg_values
        self.avg_tree.insert('', tk.END, values=avg_row, tags=('avg_row',))
        self.avg_tree.column('#0', width=0, stretch=False)

    def _resize_tree_columns(self):
        if not self.current_columns:
            return
            
        total_width = self.tree.winfo_width()
        if total_width > 100:
            fixed_width = 0
            for col in self.current_columns[:-1]:
                if col == 'FRAME_TIME':
                    fixed_width += 180
                elif col == 'FRAME_NUM':
                    fixed_width += 100
                else:
                    fixed_width += 120
            
            last_col = self.current_columns[-1]
            remaining_width = max(100, total_width - fixed_width - 25)
            self.tree.column(last_col, width=remaining_width, minwidth=100)
        
        self._sync_avg_table()
        
    def _validate_number_input(self, value):
        if value == "" or value == "-":
            return True
        pattern = r'^-?\d*\.?\d*$'
        return bool(re.match(pattern, value))
    
    def _format_datetime(self, datetime_str):
        if not datetime_str:
            return "—"
        try:
            if 'T' in datetime_str:
                dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                return dt.strftime("%d.%m.%Y %H:%M:%S")
            else:
                return datetime_str.replace('T', ' ').replace('Z', '')
        except:
            return datetime_str
    
    def _format_number(self, value):
        if value is None or value == '—':
            return "—"
        try:
            num = float(value)
            if abs(num - round(num)) < 0.0001:
                return str(int(round(num)))
            else:
                if abs(num) >= 100:
                    return f"{num:.1f}"
                elif abs(num) >= 10:
                    return f"{num:.2f}"
                else:
                    return f"{num:.3f}"
        except (ValueError, TypeError):
            return str(value)
    
    def _get_db_connection(self):
        return sqlite3.connect(self.db_path)
    
    def _try_convert_to_float(self, value):
        if value is None or value == 'NULL' or value == '':
            return None
        try:
            if isinstance(value, str):
                value = value.replace(',', '.')
                return float(value)
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _load_experiments_list(self):
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("PRAGMA table_info(Exp_info)")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                has_description = 'DESCRIPTION' in column_names
                
                # Получаем все эксперименты с описанием
                if has_description:
                    cursor.execute("""
                        SELECT EXP_ID, OPERATOR_FIO, EXP_DATE, CREATE_DATE, DESCRIPTION
                        FROM Exp_info 
                        ORDER BY EXP_DATE DESC
                    """)
                    experiments = cursor.fetchall()
                else:
                    cursor.execute("""
                        SELECT EXP_ID, OPERATOR_FIO, EXP_DATE, CREATE_DATE
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
                for exp_row in experiments:
                    exp_id = exp_row[0]
                    operator_fio = exp_row[1]
                    exp_date = exp_row[2]
                    create_date = exp_row[3]
                    description = exp_row[4] if len(exp_row) > 4 else "Нет описания"
                    
                    if operator_fio not in operators:
                        operators[operator_fio] = []
                    
                    exp_date_str = self._format_datetime(exp_date) if exp_date else "дата не указана"
                    
                    # Обрезаем описание, если оно слишком длинное (максимум 50 символов)
                    desc_short = description[:50] + "..." if len(description) > 50 else description
                    
                    # Формат: ID | Дата | Описание
                    exp_str = f"ID:{exp_id} | {exp_date_str} | {desc_short}"
                    operators[operator_fio].append((exp_id, exp_str, description))
                
                self.operators_data = operators
                operator_list = list(operators.keys())
                operator_list.sort()
                self.operator_combo['values'] = operator_list
                
                if operator_list:
                    self.operator_combo.set(operator_list[0])
                    self._on_operator_selected()
                    
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка БД", f"Не удалось загрузить список экспериментов: {e}")
    
    def _on_operator_selected(self, event=None):
        # Очищаем поля фильтра
        self.filter_min_var.set("")
        self.filter_max_var.set("")
        
        operator = self.operator_var.get()
        if operator and operator in self.operators_data:
            experiments = [exp_str for exp_id, exp_str, desc in self.operators_data[operator]]
            experiments.sort(reverse=True)
            self.exp_combo['values'] = experiments
            if experiments:
                self.exp_combo.set(experiments[0])
                self._on_experiment_selected()

    def _on_experiment_selected(self, event=None):
        # Очищаем поля фильтра
        self.filter_min_var.set("")
        self.filter_max_var.set("")
        
        exp_str = self.exp_var.get()
        if not exp_str:
            return
        
        try:
            exp_id = int(exp_str.split('|')[0].replace('ID:', '').strip())
            self.current_exp_id = exp_id
            self._load_experiment_data(exp_id)
        except (ValueError, IndexError) as e:
            messagebox.showerror("Ошибка", f"Не удалось определить ID эксперимента: {e}")
    
    def _load_experiment_data(self, exp_id):
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT OPERATOR_FIO, EXP_DATE, CREATE_DATE 
                    FROM Exp_info 
                    WHERE EXP_ID = ?
                """, (exp_id,))
                exp_info = cursor.fetchone()
                
                if exp_info:
                    self.current_operator, exp_date, create_date = exp_info
                    self.current_exp_date = self._format_datetime(exp_date)
                    self.title = f"Работа с данными - Эксперимент #{exp_id} | Оператор: {self.current_operator} | Дата: {self.current_exp_date}"
                    if self.parent and hasattr(self.parent, 'master') and hasattr(self.parent.master, 'title'):
                        self.parent.master.title(self.title)
                
                cursor.execute("PRAGMA table_info(Measurements)")
                all_columns = cursor.fetchall()
                
                if not all_columns:
                    messagebox.showwarning("Предупреждение", "Таблица Measurements не найдена в БД")
                    return
                
                exclude_columns = {'id', 'EXP_ID'}
                data_columns = [col[1] for col in all_columns if col[1] not in exclude_columns]
                
                if not data_columns:
                    messagebox.showwarning("Предупреждение", "В таблице Measurements нет столбцов с данными")
                    return
                
                columns_str = ', '.join(data_columns)
                cursor.execute(f"""
                    SELECT {columns_str}
                    FROM Measurements 
                    WHERE EXP_ID = ?
                    ORDER BY FRAME_NUM
                """, (exp_id,))
                
                rows = cursor.fetchall()
                
                if not rows:
                    messagebox.showinfo("Информация", f"В эксперименте #{exp_id} нет данных")
                    self.current_data = []
                    self.current_columns = data_columns
                    self.original_data = []
                    self._update_table()
                    return
                
                # Преобразуем данные (FRAME_NUM как целое число)
                converted_rows = []
                for row in rows:
                    converted_row = []
                    for i, value in enumerate(row):
                        col_name = data_columns[i]
                        if col_name == 'FRAME_TIME':
                            converted_row.append(self._format_datetime(value))
                        elif col_name == 'FRAME_NUM':
                            try:
                                converted_row.append(int(float(value)) if value is not None else None)
                            except (ValueError, TypeError):
                                converted_row.append(None)
                        else:
                            converted_row.append(self._try_convert_to_float(value))
                    converted_rows.append(converted_row)
                
                self.current_columns = data_columns
                self.current_data = converted_rows
                self.original_data = [row[:] for row in converted_rows]
                
                # Создаем словарь соответствия русских названий английским для фильтрации
                self.filter_channel_map = {}
                for col in self.current_columns:
                    if col not in ['FRAME_NUM', 'FRAME_TIME']:
                        rus_name = self._get_russian_column_name(col)
                        self.filter_channel_map[rus_name] = col
                
                self._update_table()
                
                # Обновляем список каналов для фильтрации (включая Кадр)
                filter_columns = ['Кадр'] + [self._get_russian_column_name(col) for col in data_columns if col not in ['FRAME_NUM', 'FRAME_TIME']]
                self.filter_channel_combo['values'] = filter_columns
                if filter_columns:
                    self.filter_channel_combo.set(filter_columns[0])
                
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка БД", f"Не удалось загрузить данные: {e}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка: {e}")
    
    def _update_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not self.current_data or not self.current_columns:
            self._sync_avg_table()
            return
        
        self.display_columns = [self._get_russian_column_name(col) for col in self.current_columns]
        
        self.tree['columns'] = self.current_columns
        for i, col in enumerate(self.current_columns):
            display_name = self.display_columns[i]
            self.tree.heading(col, text=display_name, command=lambda c=col: self._sort_by_column(c))
            
            if col == 'FRAME_TIME':
                self.tree.column(col, width=180, minwidth=150)
            elif col == 'FRAME_NUM':
                self.tree.column(col, width=100, minwidth=80)
            else:
                self.tree.column(col, width=120, minwidth=100)
        
        for row in self.current_data:
            str_row = []
            for i, val in enumerate(row):
                col_name = self.current_columns[i]
                if col_name == 'FRAME_NUM':
                    str_row.append(str(val) if val is not None else "—")
                elif col_name == 'FRAME_TIME':
                    str_row.append(val if val else "—")
                else:
                    str_row.append(self._format_number(val))
            self.tree.insert('', tk.END, values=str_row)
        
        self._sync_avg_table()
        self.root.update_idletasks()
        self._resize_tree_columns()
    
    def _sort_by_column(self, col):
        col_index = self.current_columns.index(col)
        
        if self.last_sort_column == col:
            self.last_sort_reverse = not self.last_sort_reverse
        else:
            self.last_sort_column = col
            self.last_sort_reverse = False
        
        def get_sort_key(row):
            if col_index >= len(row):
                return float('inf') if self.last_sort_reverse else float('-inf')
            val = row[col_index]
            if val is None or val == '—':
                return float('inf') if self.last_sort_reverse else float('-inf')
            try:
                if isinstance(val, str):
                    val_clean = val.replace(' ', '').replace(',', '.')
                    return float(val_clean)
                return float(val)
            except (ValueError, TypeError):
                return str(val)
        
        self.current_data.sort(key=get_sort_key, reverse=self.last_sort_reverse)
        self._update_table()
    
    def _on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "heading":
            column = self.tree.identify_column(event.x)
            if column:
                col_index = int(column.replace('#', '')) - 1
                if col_index < len(self.current_columns):
                    col_name = self.current_columns[col_index]
                    self._sort_by_column(col_name)
    
    def _apply_filter(self):
        channel = self.filter_channel_var.get()
        min_val = self.filter_min_var.get().strip()
        max_val = self.filter_max_var.get().strip()
        
        if not channel:
            messagebox.showwarning("Предупреждение", "Выберите канал для фильтрации")
            return
        
        if not min_val and not max_val:
            messagebox.showwarning("Предупреждение", "Укажите хотя бы одну границу диапазона")
            return
        
        filtered_data = [row[:] for row in self.original_data]
        
        # Определяем индекс колонки по русскому названию
        if channel == 'Кадр':
            if 'FRAME_NUM' not in self.current_columns:
                messagebox.showwarning("Предупреждение", "Столбец 'Кадр' не найден")
                return
            col_index = self.current_columns.index('FRAME_NUM')
            is_frame_filter = True
        else:
            # Получаем английское название канала из словаря соответствия
            if channel not in self.filter_channel_map:
                messagebox.showwarning("Предупреждение", f"Канал '{channel}' не найден в данных")
                return
            eng_channel_name = self.filter_channel_map[channel]
            col_index = self.current_columns.index(eng_channel_name)
            is_frame_filter = False
        
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
        
        temp_data = []
        for row in filtered_data:
            if col_index >= len(row):
                continue
            value = row[col_index]
            if value is None:
                continue
            
            if is_frame_filter:
                try:
                    float_val = int(float(value))
                except (ValueError, TypeError):
                    continue
            else:
                try:
                    float_val = float(value) if not isinstance(value, str) else float(value.replace(',', '.'))
                except (ValueError, TypeError):
                    continue
            
            min_ok = True
            max_ok = True
            if min_float is not None:
                min_ok = float_val >= min_float
            if max_float is not None:
                max_ok = float_val <= max_float
            
            if min_ok and max_ok:
                temp_data.append(row)
        
        if temp_data:
            self.current_data = temp_data
            self._update_table()
            messagebox.showinfo("Информация", f"Найдено {len(temp_data)} записей из {len(self.original_data)}")
        else:
            messagebox.showinfo("Информация", "По заданному фильтру данные не найдены")
    
    def _reset_filter(self):
        self.filter_min_var.set("")
        self.filter_max_var.set("")
        
        if self.original_data:
            self.current_data = [row[:] for row in self.original_data]
            self.last_sort_column = None
            self.last_sort_reverse = False
            self._update_table()
    
    def _sanitize_filename(self, filename):
        return re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    def _export_to_csv(self):
        if not self.current_data or not self.current_columns:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
            return
        
        operator_surname = self.current_operator.split()[0] if self.current_operator else "Unknown"
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{operator_surname}_{current_time}_exp{self.current_exp_id}"
        filename = self._sanitize_filename(filename)
        
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
                writer.writerow(self.display_columns)
                for row in self.current_data:
                    writer.writerow(row)
            messagebox.showinfo("Успех", f"Данные успешно экспортированы в файл:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", f"Не удалось сохранить файл: {e}")