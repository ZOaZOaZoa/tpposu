import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from DataManagement.data_management_program import DataManagementProgram as DataManagement

class MainApplication:
    def __init__(self, root, db_paths):
        self.root = root
        self.root.title("Главное окно с вкладками")
        self.root.geometry("1400x800")
        
        # Создаем Notebook (контейнер для вкладок)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Словарь для хранения экземпляров DataManagement
        self.data_managers = {}
        
        # Создаем вкладки с разными экземплярами DataManagement
        for tab_name, db_path in db_paths.items():
            # Создаем фрейм для вкладки
            tab_frame = ttk.Frame(self.notebook)
            self.notebook.add(tab_frame, text=tab_name)
            
            # Создаем экземпляр DataManagement для этой вкладки
            self.data_managers[tab_name] = DataManagement(db_path, tab_frame, tab_name)
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

def main():
    """Точка входа"""
    root = tk.Tk()
    
    # Пути к разным БД для разных вкладок
    db_paths = {
        "Измерения 1": Path(__file__).parent / "measurements.db",
        "Измерения 2": Path(__file__).parent / "measurements.db",
        "Архив": Path(__file__).parent / "measurements.db"
    }
    
    # Проверяем существование БД
    for name, db_path in db_paths.items():
        if not db_path.exists():
            print(f"Внимание: База данных '{db_path}' не найдена.")
            response = messagebox.askyesno("Предупреждение", 
                                          f"База данных '{db_path}' для вкладки '{name}' не найдена.\n"
                                          "Вы хотите продолжить (будет создана новая БД)?")
            if not response:
                return
    
    # Создаем и запускаем программу
    app = MainApplication(root, db_paths)
    app.run()

if __name__ == "__main__":
    main()