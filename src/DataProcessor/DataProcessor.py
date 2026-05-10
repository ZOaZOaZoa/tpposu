import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv

class DataProcessor:
    def __init__(self, parent=None, tab_name: str = ''):
        self.parent = parent
        self.title = "Просмотр CSV файла"
        self.current_file = None
        self._setup_ui()

    def _setup_ui(self):
        """Настройка пользовательского интерфейса"""
        
        # Основной контейнер с возможностью изменения размера
        self.main_paned = ttk.PanedWindow(self.parent, orient=tk.VERTICAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Верхняя панель (фиксированная часть)
        self.top_container = ttk.Frame(self.main_paned)
        self.main_paned.add(self.top_container, weight=0)
        
        # Панель управления
        self.control_frame = ttk.LabelFrame(self.top_container, text="Управление", padding=10)
        self.control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Центрируем кнопки
        buttons_inner_frame = ttk.Frame(self.control_frame)
        buttons_inner_frame.pack(anchor=tk.CENTER)
        
        self.open_button = ttk.Button(buttons_inner_frame, text="Открыть CSV файл", command=self.open_file, width=20)
        self.open_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(buttons_inner_frame, text="Очистить таблицу", command=self.clear_table, width=20)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Информация о файле
        self.file_info_label = ttk.Label(self.top_container, text="", font=('Arial', 9))
        self.file_info_label.pack(anchor=tk.W, padx=10, pady=5)
        
        # Панель таблицы
        self.table_container = ttk.Frame(self.main_paned)
        self.main_paned.add(self.table_container, weight=1)
        
        # Создаем фрейм для таблицы
        self.table_frame = ttk.LabelFrame(self.table_container, text="Данные", padding=10)
        self.table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Создаем Treeview с прокруткой
        self.tree_frame = ttk.Frame(self.table_frame)
        self.tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(self.tree_frame, show='headings')
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
        
        self.rows_count_label = ttk.Label(self.status_frame, text="", font=('Arial', 9))
        self.rows_count_label.pack(side=tk.RIGHT)

    def open_file(self):
        """Открытие CSV файла"""
        file_path = filedialog.askopenfilename(
            title="Выберите CSV файл",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        self.current_file = file_path
        self.load_csv(file_path)

    def load_csv(self, file_path):
        """Загрузка и отображение CSV файла"""
        try:
            # Очищаем предыдущие данные
            self.clear_table()
            
            # Определяем кодировку
            encodings = ['utf-8-sig', 'utf-8', 'cp1251', 'latin1']
            data = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        reader = csv.reader(file)
                        data = list(reader)
                    break
                except UnicodeDecodeError:
                    continue
            
            if data is None:
                raise Exception("Не удалось определить кодировку файла")
            
            if not data:
                raise Exception("Файл пуст")
            
            # Первая строка - заголовки
            headers = data[0]
            rows = data[1:]
            
            # Настройка колонок
            self.setup_columns(headers)
            
            # Заполнение данными
            self.populate_table(rows)
            
            # Обновление информации
            file_name = file_path.split('/')[-1]
            self.file_info_label.config(text=f"Файл: {file_name}")
            self.rows_count_label.config(text=f"Строк: {len(rows)}")
            self.status_label.config(text=f"Загружено {len(rows)} строк из {file_name}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл:\n{str(e)}")
            self.status_label.config(text="Ошибка загрузки файла")

    def setup_columns(self, headers):
        """Настройка колонок таблицы"""
        # Очистка существующих колонок
        self.tree['columns'] = headers
        
        # Настройка каждой колонки
        for col in headers:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c))
            
            # Автоматическая ширина на основе длины заголовка
            width = min(max(len(str(col)) * 10, 100), 300)
            self.tree.column(col, width=width, minwidth=80, anchor='center')

    def populate_table(self, rows):
        """Заполнение таблицы данными"""
        for row in rows:
            # Обрезаем строку до количества колонок
            if len(row) < len(self.tree['columns']):
                row.extend([''] * (len(self.tree['columns']) - len(row)))
            elif len(row) > len(self.tree['columns']):
                row = row[:len(self.tree['columns'])]
            
            self.tree.insert('', 'end', values=row)

    def sort_column(self, col):
        """Сортировка по колонке"""
        # Получаем все элементы
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]
        
        # Пробуем сортировать как числа
        try:
            # Заменяем запятые на точки для чисел
            items.sort(key=lambda x: float(x[0].replace(',', '.')))
        except (ValueError, AttributeError):
            try:
                # Пробуем сортировать как числа с возможными пробелами
                items.sort(key=lambda x: float(''.join(x[0].split())))
            except (ValueError, AttributeError):
                # Сортируем как строки
                items.sort(key=lambda x: str(x[0]))
        
        # Переупорядочиваем
        for index, (_, item) in enumerate(items):
            self.tree.move(item, '', index)
        
        # Обновляем статус
        self.status_label.config(text=f"Отсортировано по колонке: {col}")

    def clear_table(self):
        """Очистка таблицы"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.current_file = None
        self.file_info_label.config(text="")
        self.rows_count_label.config(text="")
        self.status_label.config(text="Таблица очищена")