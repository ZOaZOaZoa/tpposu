import tkinter as tk
from tkinter import ttk
from pathlib import Path
from dataclasses import dataclass
from typing import Protocol, Any

from DataManagement import DataManagement
from Registartor import Registrator

class ModuleClass(Protocol):
    def __init__(self, parent=None, tab_name: str = '', **kwargs):
        ...
    

@dataclass
class Module:
    tab_name: str
    kwargs: dict[str, Any]
    module_class: ModuleClass

    def create_instance(self, parent):
        return self.module_class(
            parent = parent,
            tab_name = self.tab_name,
            **self.kwargs,
        )


class MainApplication:
    def __init__(self, root, modules: list[Module]):
        self.root = root
        self.root.geometry("1400x800")
        
        # Создаем Notebook (контейнер для вкладок)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Словарь для хранения экземпляров DataManagement
        self.tabs = {}
        
        # Создаем вкладки с разными экземплярами DataManagement
        for module in modules:
            # Создаем фрейм для вкладки
            tab_frame = ttk.Frame(self.notebook)
            tab_name = module.tab_name
            self.notebook.add(tab_frame, text=tab_name)
            
            module_instance = module.create_instance(parent=tab_frame)

            # Создаем экземпляр DataManagement для этой вкладки
            self.tabs[tab_name] = module_instance
        
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)
    
    def _on_tab_changed(self, event):
        '''
            Обновление названия окна в соответствии с title модуля во вкладке
        '''
        current_tab = self.notebook.select()

        if current_tab:
            tab_name = self.notebook.tab(current_tab, "text")
            current_module = self.tabs[tab_name]
            self.root.title(current_module.title)
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

def main():
    """Точка входа"""
    root = tk.Tk()
    
    db_path = Path(__file__).parent / "measurements.db"
    modules = [
        Module(
            tab_name='Регистратор',
            module_class=Registrator,
            kwargs={}
        ),
        Module(
            tab_name='Работа с данными',
            module_class=DataManagement,
            kwargs={
                'db_path': db_path,
            }
        ),
    ]
    
    # Создаем и запускаем программу
    app = MainApplication(root, modules)
    app.run()

if __name__ == "__main__":
    main()