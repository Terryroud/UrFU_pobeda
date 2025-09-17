import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from pathlib import Path
from typing import Dict, List, Any
import os

class JSONEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Редактор векторов и паттернов")
        self.root.geometry("1200x800")
        
        self.patterns_file = "patterns.json"
        self.vectors_file = "vectors.json"
        
        self.patterns_data = {}
        self.vectors_data = {"vectors": []}
        
        self.load_data()
        self.create_widgets()
        self.update_display()
    
    def load_data(self):
        """Загружает данные из JSON файлов"""
        try:
            if Path(self.patterns_file).exists():
                with open(self.patterns_file, 'r', encoding='utf-8') as f:
                    self.patterns_data = json.load(f)
            else:
                self.patterns_data = {
                    "CRITICAL": [],
                    "HIGH": [],
                    "MEDIUM": []
                }
            
            if Path(self.vectors_file).exists():
                with open(self.vectors_file, 'r', encoding='utf-8') as f:
                    self.vectors_data = json.load(f)
            else:
                self.vectors_data = {"vectors": []}
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка загрузки файлов: {e}")
    
    def save_data(self):
        """Сохраняет данные в JSON файлы"""
        try:
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                json.dump(self.patterns_data, f, ensure_ascii=False, indent=2)
            
            with open(self.vectors_file, 'w', encoding='utf-8') as f:
                json.dump(self.vectors_data, f, ensure_ascii=False, indent=2)
                
            messagebox.showinfo("Успех", "Файлы успешно сохранены!")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка сохранения: {e}")
    
    def create_widgets(self):
        """Создает элементы интерфейса"""
        # Создаем notebook для вкладок
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Вкладка для patterns.json
        patterns_frame = ttk.Frame(notebook)
        notebook.add(patterns_frame, text="Patterns (Уровни угроз)")
        
        # Вкладка для vectors.json
        vectors_frame = ttk.Frame(notebook)
        notebook.add(vectors_frame, text="Vectors (Векторы)")
        
        # Создаем элементы для patterns.json
        self.create_patterns_tab(patterns_frame)
        
        # Создаем элементы для vectors.json
        self.create_vectors_tab(vectors_frame)
        
        # Кнопки управления внизу
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(button_frame, text="Сохранить", command=self.save_data).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Обновить", command=self.update_display).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Загрузить из файла", command=self.load_from_file).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Экспорт", command=self.export_data).pack(side='left', padx=5)
    
    def create_patterns_tab(self, parent):
        """Создает интерфейс для редактирования patterns.json"""
        # Фрейм для выбора уровня
        level_frame = ttk.Frame(parent)
        level_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(level_frame, text="Уровень угрозы:").pack(side='left')
        self.level_var = tk.StringVar()
        level_combo = ttk.Combobox(level_frame, textvariable=self.level_var, 
                                  values=list(self.patterns_data.keys()))
        level_combo.pack(side='left', padx=5)
        level_combo.bind('<<ComboboxSelected>>', self.on_level_select)
        
        # Фрейм для добавления паттернов
        add_frame = ttk.Frame(parent)
        add_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(add_frame, text="Новый паттерн:").pack(side='left')
        self.new_pattern_var = tk.StringVar()
        pattern_entry = ttk.Entry(add_frame, textvariable=self.new_pattern_var, width=30)
        pattern_entry.pack(side='left', padx=5)
        
        ttk.Button(add_frame, text="Добавить", command=self.add_pattern).pack(side='left', padx=5)
        
        # Текстовое поле для отображения паттернов
        ttk.Label(parent, text="Паттерны выбранного уровня:").pack(anchor='w', padx=10, pady=(10, 0))
        
        self.patterns_text = scrolledtext.ScrolledText(parent, height=15, width=50)
        self.patterns_text.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Фрейм для управления паттернами
        manage_frame = ttk.Frame(parent)
        manage_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(manage_frame, text="Удалить выбранный", command=self.delete_pattern).pack(side='left', padx=5)
        ttk.Button(manage_frame, text="Очистить все", command=self.clear_patterns).pack(side='left', padx=5)
    
    def create_vectors_tab(self, parent):
        """Создает интерфейс для редактирования vectors.json"""
        # Фрейм для выбора вектора
        vector_frame = ttk.Frame(parent)
        vector_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(vector_frame, text="Вектор:").pack(side='left')
        self.vector_var = tk.StringVar()
        self.vector_combo = ttk.Combobox(vector_frame, textvariable=self.vector_var, width=30)
        self.vector_combo.pack(side='left', padx=5)
        self.vector_combo.bind('<<ComboboxSelected>>', self.on_vector_select)
        
        ttk.Button(vector_frame, text="Новый вектор", command=self.create_new_vector).pack(side='left', padx=5)
        ttk.Button(vector_frame, text="Удалить вектор", command=self.delete_vector).pack(side='left', padx=5)
        
        # Фрейм для редактирования свойств вектора
        props_frame = ttk.LabelFrame(parent, text="Свойства вектора")
        props_frame.pack(fill='x', padx=10, pady=5)
        
        # Название
        name_frame = ttk.Frame(props_frame)
        name_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(name_frame, text="Название:").pack(side='left')
        self.vector_name_var = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.vector_name_var, width=40).pack(side='left', padx=5)
        
        # Описание
        desc_frame = ttk.Frame(props_frame)
        desc_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(desc_frame, text="Описание:").pack(side='left')
        self.vector_desc_var = tk.StringVar()
        ttk.Entry(desc_frame, textvariable=self.vector_desc_var, width=40).pack(side='left', padx=5)
        
        # Вес
        weight_frame = ttk.Frame(props_frame)
        weight_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(weight_frame, text="Вес:").pack(side='left')
        self.vector_weight_var = tk.DoubleVar(value=1.0)
        ttk.Spinbox(weight_frame, from_=0.1, to=10.0, increment=0.1, 
                   textvariable=self.vector_weight_var, width=10).pack(side='left', padx=5)
        
        ttk.Button(props_frame, text="Сохранить свойства", command=self.save_vector_props).pack(pady=5)
        
        # Фрейм для управления паттернами вектора
        patterns_frame = ttk.LabelFrame(parent, text="Паттерны вектора")
        patterns_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Добавление паттернов
        add_pattern_frame = ttk.Frame(patterns_frame)
        add_pattern_frame.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(add_pattern_frame, text="Новый паттерн:").pack(side='left')
        self.new_vector_pattern_var = tk.StringVar()
        ttk.Entry(add_pattern_frame, textvariable=self.new_vector_pattern_var, width=30).pack(side='left', padx=5)
        ttk.Button(add_pattern_frame, text="Добавить", command=self.add_vector_pattern).pack(side='left', padx=5)
        
        # Список паттернов
        self.vector_patterns_listbox = tk.Listbox(patterns_frame, height=10)
        self.vector_patterns_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Кнопки управления паттернами
        pattern_buttons_frame = ttk.Frame(patterns_frame)
        pattern_buttons_frame.pack(fill='x', padx=5, pady=2)
        
        ttk.Button(pattern_buttons_frame, text="Удалить выбранный", 
                  command=self.delete_vector_pattern).pack(side='left', padx=5)
        ttk.Button(pattern_buttons_frame, text="Очистить все", 
                  command=self.clear_vector_patterns).pack(side='left', padx=5)
    
    def update_display(self):
        """Обновляет отображение данных"""
        self.load_data()
        
        # Обновляем комбобокс уровней
        if hasattr(self, 'level_var'):
            self.level_var.set('')
        
        # Обновляем комбобокс векторов
        if hasattr(self, 'vector_combo'):
            vector_names = [v['name'] for v in self.vectors_data['vectors']]
            self.vector_combo['values'] = vector_names
            if vector_names:
                self.vector_combo.set(vector_names[0])
                self.on_vector_select(None)
            else:
                self.vector_var.set('')
                self.clear_vector_fields()
    
    def on_level_select(self, event):
        """Обработчик выбора уровня"""
        level = self.level_var.get()
        if level in self.patterns_data:
            patterns = '\n'.join(self.patterns_data[level])
            self.patterns_text.delete(1.0, tk.END)
            self.patterns_text.insert(1.0, patterns)
    
    def on_vector_select(self, event):
        """Обработчик выбора вектора"""
        vector_name = self.vector_var.get()
        for vector in self.vectors_data['vectors']:
            if vector['name'] == vector_name:
                self.vector_name_var.set(vector['name'])
                self.vector_desc_var.set(vector['description'])
                self.vector_weight_var.set(vector.get('weight', 1.0))
                
                # Обновляем список паттернов
                self.vector_patterns_listbox.delete(0, tk.END)
                for pattern in vector['patterns']:
                    self.vector_patterns_listbox.insert(tk.END, pattern)
                break
    
    def add_pattern(self):
        """Добавляет паттерн в выбранный уровень"""
        level = self.level_var.get()
        pattern = self.new_pattern_var.get().strip()
        
        if not level:
            messagebox.showwarning("Внимание", "Выберите уровень угрозы!")
            return
        
        if not pattern:
            messagebox.showwarning("Внимание", "Введите паттерн!")
            return
        
        if pattern in self.patterns_data[level]:
            messagebox.showwarning("Внимание", "Такой паттерн уже существует!")
            return
        
        self.patterns_data[level].append(pattern)
        self.patterns_text.insert(tk.END, f"\n{pattern}")
        self.new_pattern_var.set('')
    
    def delete_pattern(self):
        """Удаляет выбранный паттерн"""
        level = self.level_var.get()
        if not level:
            return
        
        selection = self.patterns_text.tag_ranges(tk.SEL)
        if selection:
            selected_text = self.patterns_text.get(selection[0], selection[1]).strip()
            if selected_text in self.patterns_data[level]:
                self.patterns_data[level].remove(selected_text)
                self.patterns_text.delete(selection[0], selection[1])
    
    def clear_patterns(self):
        """Очищает все паттерны выбранного уровня"""
        level = self.level_var.get()
        if not level:
            return
        
        if messagebox.askyesno("Подтверждение", "Очистить все паттерны этого уровня?"):
            self.patterns_data[level] = []
            self.patterns_text.delete(1.0, tk.END)
    
    def create_new_vector(self):
        """Создает новый вектор"""
        new_name = f"NEW_VECTOR_{len(self.vectors_data['vectors']) + 1}"
        new_vector = {
            "name": new_name,
            "description": "Новое описание",
            "patterns": [],
            "weight": 1.0
        }
        self.vectors_data['vectors'].append(new_vector)
        self.update_display()
        self.vector_var.set(new_name)
        self.on_vector_select(None)
    
    def delete_vector(self):
        """Удаляет выбранный вектор"""
        vector_name = self.vector_var.get()
        if not vector_name:
            return
        
        if messagebox.askyesno("Подтверждение", f"Удалить вектор '{vector_name}'?"):
            self.vectors_data['vectors'] = [
                v for v in self.vectors_data['vectors'] if v['name'] != vector_name
            ]
            self.update_display()
    
    def save_vector_props(self):
        """Сохраняет свойства вектора"""
        vector_name = self.vector_var.get()
        if not vector_name:
            return
        
        for vector in self.vectors_data['vectors']:
            if vector['name'] == vector_name:
                vector['name'] = self.vector_name_var.get()
                vector['description'] = self.vector_desc_var.get()
                vector['weight'] = self.vector_weight_var.get()
                break
        
        self.update_display()
        self.vector_var.set(self.vector_name_var.get())
    
    def add_vector_pattern(self):
        """Добавляет паттерн в вектор"""
        vector_name = self.vector_var.get()
        pattern = self.new_vector_pattern_var.get().strip()
        
        if not vector_name:
            messagebox.showwarning("Внимание", "Выберите вектор!")
            return
        
        if not pattern:
            messagebox.showwarning("Внимание", "Введите паттерн!")
            return
        
        for vector in self.vectors_data['vectors']:
            if vector['name'] == vector_name:
                if pattern in vector['patterns']:
                    messagebox.showwarning("Внимание", "Такой паттерн уже существует!")
                    return
                
                vector['patterns'].append(pattern)
                self.vector_patterns_listbox.insert(tk.END, pattern)
                self.new_vector_pattern_var.set('')
                break
    
    def delete_vector_pattern(self):
        """Удаляет выбранный паттерн из вектора"""
        vector_name = self.vector_var.get()
        selection = self.vector_patterns_listbox.curselection()
        
        if not vector_name or not selection:
            return
        
        pattern = self.vector_patterns_listbox.get(selection[0])
        for vector in self.vectors_data['vectors']:
            if vector['name'] == vector_name:
                if pattern in vector['patterns']:
                    vector['patterns'].remove(pattern)
                    self.vector_patterns_listbox.delete(selection[0])
                break
    
    def clear_vector_patterns(self):
        """Очищает все паттерны вектора"""
        vector_name = self.vector_var.get()
        if not vector_name:
            return
        
        if messagebox.askyesno("Подтверждение", "Очистить все паттерны этого вектора?"):
            for vector in self.vectors_data['vectors']:
                if vector['name'] == vector_name:
                    vector['patterns'] = []
                    self.vector_patterns_listbox.delete(0, tk.END)
                    break
    
    def clear_vector_fields(self):
        """Очищает поля вектора"""
        self.vector_name_var.set('')
        self.vector_desc_var.set('')
        self.vector_weight_var.set(1.0)
        self.vector_patterns_listbox.delete(0, tk.END)
    
    def load_from_file(self):
        """Загружает данные из выбранного файла"""
        file_path = filedialog.askopenfilename(
            title="Выберите JSON файл",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if 'vectors' in data:
                    self.vectors_file = file_path
                    self.vectors_data = data
                else:
                    self.patterns_file = file_path
                    self.patterns_data = data
                
                self.update_display()
                messagebox.showinfo("Успех", "Файл загружен!")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка загрузки файла: {e}")
    
    def export_data(self):
        """Экспортирует данные в файл"""
        file_path = filedialog.asksaveasfilename(
            title="Сохранить как",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                # Определяем тип данных для экспорта
                if 'vectors' in self.vectors_data:
                    data_to_export = self.vectors_data
                else:
                    data_to_export = self.patterns_data
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data_to_export, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("Успех", "Данные экспортированы!")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка экспорта: {e}")

def main():
    """Запуск приложения"""
    root = tk.Tk()
    app = JSONEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
