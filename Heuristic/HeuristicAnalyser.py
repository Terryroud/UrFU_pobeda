
import json
import logging
import re
import os
import sys
import tkinter as tk
import threading
import webbrowser
from typing import List, Tuple, Optional, Dict, Set, Any
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from tkinter import ttk, messagebox, filedialog, scrolledtext

try:
    from flask import Flask, render_template, request, jsonify
except Exception:
    Flask = None
    render_template = None
    request = None
    jsonify = None

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"prompt_security_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PromptSecurity")

class HeuristicFilter:
    def __init__(self, text: str, patterns_file: str = "patterns.json"):
        self.text = text
        # Загружаем паттерны из json
        with open(patterns_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.INJECTION_PATTERNS = data.get("INJECTION_PATTERNS", [])

    def detect_injection(self) -> bool:
        # Проверка текста на совпадение хотя бы с одним паттерном
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, self.text, re.IGNORECASE):
                return True
        return False

@dataclass
class ThreatVector:
    name: str
    description: str
    patterns: List[str]
    weight: float = 1.0
    risk_score: float = 0.0  # Будет вычисляться динамически

class PromptInjectionClassifier:
    def __init__(self, text: str, vectors_file: str = "vectors.json"):
        self.text = text.lower()
        self.vectors_file = vectors_file
        self.threat_vectors: List[ThreatVector] = []
        self.detected_patterns: List[Tuple[str, float, str]] = []  # (pattern, similarity, vector_name)
        self._load_vectors()
        logger.info(f"Инициализирован классификатор для текста длиной {len(self.text)} символов")
        
    def _load_vectors(self):
        """Загружает векторы угроз из JSON файла"""
        try:
            if not Path(self.vectors_file).exists():
                logger.error(f"Файл векторов {self.vectors_file} не найден!")
                raise FileNotFoundError(f"Файл векторов {self.vectors_file} не существует")
                
            with open(self.vectors_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            self.threat_vectors.clear()
            vector_count = 0
            pattern_count = 0
            
            for vector_data in data.get("vectors", []):
                vector = ThreatVector(
                    name=vector_data["name"],
                    description=vector_data["description"],
                    patterns=vector_data["patterns"],
                    weight=vector_data.get("weight", 1.0)
                )
                self.threat_vectors.append(vector)
                vector_count += 1
                pattern_count += len(vector.patterns)
                
            logger.info(f"Загружено {vector_count} векторов с {pattern_count} паттернами")
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON файла векторов: {e}")
            raise
        except KeyError as e:
            logger.error(f"Отсутствует обязательное поле в файле векторов: {e}")
            raise
        except FileNotFoundError as e:
            logger.error(f"Файл векторов не найден: {e}")
            raise
        except Exception as e:
            logger.error(f"Неизвестная ошибка при загрузке векторов: {e}")
            raise

    def reload_vectors(self, new_vectors_file: str = None) -> bool:
        """
        Перезагружает векторы из файла
        
        Args:
            new_vectors_file: путь к новому файлу векторов (если None, используется текущий)
        
        Returns:
            bool: True если перезагрузка успешна, False если произошла ошибка
        """
        try:
            if new_vectors_file:
                self.vectors_file = new_vectors_file
                logger.info(f"Установлен новый файл векторов: {new_vectors_file}")
            
            # Сохраняем текущие обнаруженные паттерны перед перезагрузкой
            old_detected_patterns = self.detected_patterns.copy()
            
            self._load_vectors()
            
            # Пересчитываем обнаруженные паттерны с новыми векторами
            if old_detected_patterns:
                self.detected_patterns = []
                for pattern, similarity, old_vector_name in old_detected_patterns:
                    # Пытаемся найти соответствующий вектор в новой загрузке
                    for vector in self.threat_vectors:
                        if pattern in vector.patterns:
                            self.detected_patterns.append((pattern, similarity, vector.name))
                            break
            
            logger.info("Векторы успешно перезагружены")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка перезагрузки векторов: {e}")
            return False

    def update_vectors_from_data(self, vectors_data: List[Dict]) -> bool:
        """
        Обновляет векторы из готовых данных (без файла)
        
        Args:
            vectors_data: список словарей с данными векторов
        
        Returns:
            bool: True если обновление успешно, False если произошла ошибка
        """
        try:
            self.threat_vectors.clear()
            vector_count = 0
            pattern_count = 0
            
            for vector_data in vectors_data:
                vector = ThreatVector(
                    name=vector_data["name"],
                    description=vector_data["description"],
                    patterns=vector_data["patterns"],
                    weight=vector_data.get("weight", 1.0)
                )
                self.threat_vectors.append(vector)
                vector_count += 1
                pattern_count += len(vector.patterns)
            
            # Очищаем обнаруженные паттерны, так как векторы изменились
            self.detected_patterns.clear()
                
            logger.info(f"Векторы обновлены из данных: {vector_count} векторов с {pattern_count} паттернами")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления векторов из данных: {e}")
            return False

    def add_single_vector(self, name: str, description: str, patterns: List[str], weight: float = 1.0) -> bool:
        """
        Добавляет один вектор в текущий набор
        
        Args:
            name: название вектора
            description: описание вектора
            patterns: список паттернов
            weight: вес вектора
        
        Returns:
            bool: True если добавление успешно
        """
        try:
            # Проверяем, нет ли уже вектора с таким именем
            for vector in self.threat_vectors:
                if vector.name == name:
                    logger.warning(f"Вектор с именем '{name}' уже существует, обновляем")
                    vector.description = description
                    vector.patterns = patterns
                    vector.weight = weight
                    break
            else:
                # Если не нашли, добавляем новый
                vector = ThreatVector(name, description, patterns, weight)
                self.threat_vectors.append(vector)
            
            logger.info(f"Добавлен/обновлен вектор '{name}' с {len(patterns)} паттернами")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления вектора '{name}': {e}")
            return False

    def remove_vector(self, vector_name: str) -> bool:
        """
        Удаляет вектор по имени
        
        Args:
            vector_name: название вектора для удаления
        
        Returns:
            bool: True если удаление успешно, False если вектор не найден
        """
        for i, vector in enumerate(self.threat_vectors):
            if vector.name == vector_name:
                self.threat_vectors.pop(i)
                # Удаляем связанные обнаруженные паттерны
                self.detected_patterns = [p for p in self.detected_patterns if p[2] != vector_name]
                logger.info(f"Вектор '{vector_name}' удален")
                return True
        
        logger.warning(f"Вектор '{vector_name}' не найден для удаления")
        return False

    def clear_vectors(self) -> None:
        """Очищает все векторы и обнаруженные паттерны"""
        self.threat_vectors.clear()
        self.detected_patterns.clear()
        logger.info("Все векторы и обнаруженные паттерны очищены")

    @staticmethod
    def levenshtein(str1: str, str2: str, 
                   insertion_cost: int = 1, 
                   deletion_cost: int = 1, 
                   substitution_cost: int = 1) -> int:
        """Вычисление расстояния Левенштейна"""
        if not isinstance(str1, str) or not isinstance(str2, str):
            logger.error("Переданы не строки для вычисления расстояния Левенштейна")
            raise TypeError("Оба аргумента должны быть строками")

        if any(weight < 0 for weight in [insertion_cost, deletion_cost, substitution_cost]):
            logger.error("Отрицательные веса для расстояния Левенштейна")
            raise ValueError("Веса не могут быть отрицательными")
        
        if insertion_cost == deletion_cost == substitution_cost == 0:
            logger.error("Все веса нулевые для расстояния Левенштейна")
            raise ValueError("Все веса не могут быть нулевыми одновременно")
        
        if str1 == str2:
            return 0
        
        if len(str1) == 0:
            return len(str2) * insertion_cost
        
        if len(str2) == 0:
            return len(str1) * deletion_cost

        if len(str1) < len(str2):
            return PromptInjectionClassifier.levenshtein(str2, str1, insertion_cost, deletion_cost, substitution_cost)
        
        previous_row = [j * insertion_cost for j in range(len(str2) + 1)]
        
        for i, c1 in enumerate(str1):
            current_row = [(i + 1) * deletion_cost]
            for j, c2 in enumerate(str2):
                insertions = previous_row[j + 1] + deletion_cost
                deletions = current_row[j] + insertion_cost
                substitutions = previous_row[j] + (substitution_cost if c1 != c2 else 0)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def normalized_similarity(self, text: str, pattern: str) -> float:
        """Нормализованная схожесть 0-1"""
        try:
            distance = self.levenshtein(text, pattern)
            max_len = max(len(text), len(pattern))
            
            if max_len == 0:
                return 1.0
            
            similarity = 1.0 - (distance / max_len)
            return max(0.0, min(1.0, similarity))
        except Exception as e:
            logger.warning(f"Ошибка вычисления схожести для '{text}' и '{pattern}': {e}")
            return 0.0

    def analyze_text(self, threshold: float = 0.7) -> Dict:
        """Основной метод анализа текста"""
        logger.info(f"Начинаем анализ текста с порогом {threshold}")
        self.detected_patterns.clear()
        words = self.text.split()
        
        total_checks = 0
        detected_count = 0
        
        for vector in self.threat_vectors:
            for pattern in vector.patterns:
                # Проверяем полное совпадение для коротких паттернов
                if len(pattern.split()) <= 2:
                    total_checks += 1
                    similarity = self.normalized_similarity(self.text, pattern)
                    if similarity >= threshold:
                        self.detected_patterns.append((pattern, similarity * vector.weight, vector.name))
                        detected_count += 1
                        logger.debug(f"Обнаружен паттерн: {pattern} (схожесть: {similarity:.2f}, вектор: {vector.name})")
                
                # Проверяем отдельные слова
                pattern_words = pattern.split()
                for pattern_word in pattern_words:
                    if len(pattern_word) >= 3:
                        for text_word in words:
                            if len(text_word) >= 3:
                                total_checks += 1
                                similarity = self.normalized_similarity(text_word, pattern_word)
                                if similarity >= threshold:
                                    self.detected_patterns.append((pattern_word, similarity * vector.weight, vector.name))
                                    detected_count += 1
                                    logger.debug(f"Обнаружено слово: {pattern_word} в '{text_word}' (схожесть: {similarity:.2f}, вектор: {vector.name})")
        
        logger.info(f"Выполнено {total_checks} проверок, обнаружено {detected_count} совпадений")
        
        # Убираем дубликаты и сортируем
        self._deduplicate_and_sort()
        
        # Вычисляем риск для каждого вектора
        self._calculate_vector_risk()
        
        result = self.get_classification_result()
        self._log_classification_result(result)
        
        return result

    def _deduplicate_and_sort(self):
        """Убирает дубликаты и сортирует паттерны"""
        unique_patterns = []
        seen = set()
        
        for pattern in self.detected_patterns:
            key = (pattern[0], pattern[2])  # pattern_text + vector_name
            if key not in seen:
                unique_patterns.append(pattern)
                seen.add(key)
        
        # Сортируем по весу схожести
        unique_patterns.sort(key=lambda x: x[1], reverse=True)
        self.detected_patterns = unique_patterns
        logger.debug(f"После дедупликации осталось {len(self.detected_patterns)} уникальных паттернов")

    def _calculate_vector_risk(self):
        """Вычисляет риск для каждого вектора"""
        for vector in self.threat_vectors:
            vector_patterns = [p for p in self.detected_patterns if p[2] == vector.name]
            if vector_patterns:
                # Средний вес обнаруженных паттернов
                vector.risk_score = sum(p[1] for p in vector_patterns) / len(vector_patterns) * vector.weight
                logger.debug(f"Вектор {vector.name}: риск {vector.risk_score:.2f}")

    def get_classification_result(self) -> Dict:
        """Возвращает результат классификации"""
        total_risk = self.calculate_total_risk()
        detected_vectors = self._get_detected_vectors_info()
        
        return {
            "text": self.text,
            "total_risk_score": round(total_risk, 2),
            "is_malicious": total_risk > 0.5,  # Порог malicious
            "detected_vectors_count": len(detected_vectors),
            "detected_patterns_count": len(self.detected_patterns),
            "detected_vectors": detected_vectors,
            "recommendation": self.get_recommendation(total_risk),
            "timestamp": datetime.now().isoformat()
        }

    def _log_classification_result(self, result: Dict):
        """Логирует результат классификации"""
        if result['is_malicious']:
            logger.warning(
                f"ОБНАРУЖЕНА УГРОЗА! Общий риск: {result['total_risk_score']}, "
                f"Векторов: {result['detected_vectors_count']}, Паттернов: {result['detected_patterns_count']}"
            )
            for vector in result['detected_vectors']:
                logger.warning(
                    f"Вектор: {vector['name']} - {vector['description']}, "
                    f"Риск: {vector['risk_score']:.2f}, Паттерны: {vector['patterns']}"
                )
        else:
            logger.info("Текст безопасен, угроз не обнаружено")

    def calculate_total_risk(self) -> float:
        """Вычисляет общий скоринг риска"""
        if not self.detected_patterns:
            return 0.0
        
        # Суммируем risk_score всех векторов
        total_risk = sum(vector.risk_score for vector in self.threat_vectors if vector.risk_score > 0)
        return min(total_risk, 10.0)  # Ограничиваем максимальный risk

    def _get_detected_vectors_info(self) -> List[Dict]:
        """Возвращает информацию об обнаруженных векторах"""
        vector_info = []
        for vector in self.threat_vectors:
            if vector.risk_score > 0:
                vector_patterns = [p[0] for p in self.detected_patterns if p[2] == vector.name]
                vector_info.append({
                    "name": vector.name,
                    "description": vector.description,
                    "risk_score": round(vector.risk_score, 2),
                    "patterns": vector_patterns,
                    "pattern_count": len(vector_patterns),
                    "weight": vector.weight
                })
        
        # Сортируем по risk_score
        vector_info.sort(key=lambda x: x["risk_score"], reverse=True)
        return vector_info

    def get_recommendation(self, total_risk: float) -> str:
        """Возвращает рекомендацию на основе общего риска"""
        if total_risk >= 2.0:
            return "🚨 ВЫСОКИЙ РИСК! Немедленная блокировка запроса"
        elif total_risk >= 1.0:
            return "⚠️ СРЕДНИЙ РИСК! Требуется ручная проверка"
        elif total_risk >= 0.5:
            return "🔶 НИЗКИЙ РИСК! Рекомендуется мониторинг"
        else:
            return "✅ БЕЗОПАСНО! Запрос можно обрабатывать"

    def get_vector_stats(self) -> Dict:
        """Возвращает статистику по векторам"""
        return {
            "total_vectors": len(self.threat_vectors),
            "total_patterns": sum(len(v.patterns) for v in self.threat_vectors),
            "vectors": [
                {
                    "name": v.name,
                    "pattern_count": len(v.patterns),
                    "weight": v.weight,
                    "description": v.description
                }
                for v in self.threat_vectors
            ]
        }


#---------------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------------

class JSONEditor:
    """
    Редактор JSON-файлов:
    - patterns.json — ожидается структура: {"INJECTION_PATTERNS": [ ... ]}
    - vectors.json — структура прежняя: {"vectors": [ {name, description, patterns, weight}, ... ]}
    """
    def __init__(self, root=None, web_mode=False):
        self.web_mode = web_mode
        self.root = root
        self.patterns_file = "patterns.json"
        self.vectors_file = "vectors.json"

        # Данные в памяти
        self.patterns_data = {"INJECTION_PATTERNS": []}
        self.vectors_data = {"vectors": []}

        self.load_data()

        if not web_mode and root:
            self.create_widgets()
            self.update_display()

    def load_data(self):
        """Загружает patterns.json и vectors.json. patterns.json всегда словарь {"INJECTION_PATTERNS": [...]}."""
        try:
            # --- patterns.json ---
            if Path(self.patterns_file).exists():
                with open(self.patterns_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                # Всегда приводим к {"INJECTION_PATTERNS": [...]}
                if isinstance(loaded, dict) and "INJECTION_PATTERNS" in loaded:
                    self.patterns_data = {"INJECTION_PATTERNS": list(loaded["INJECTION_PATTERNS"])}
                elif isinstance(loaded, list):
                    self.patterns_data = {"INJECTION_PATTERNS": loaded}
                else:
                    logger.warning("Неожиданный формат patterns.json — создаю пустой")
                    self.patterns_data = {"INJECTION_PATTERNS": []}
            else:
                # Создаем пустой файл
                self.patterns_data = {"INJECTION_PATTERNS": []}
                with open(self.patterns_file, 'w', encoding='utf-8') as f:
                    json.dump(self.patterns_data, f, ensure_ascii=False, indent=2)

            # --- vectors.json ---
            if Path(self.vectors_file).exists():
                with open(self.vectors_file, 'r', encoding='utf-8') as f:
                    loaded_vectors = json.load(f)
                if isinstance(loaded_vectors, dict) and "vectors" in loaded_vectors:
                    self.vectors_data = loaded_vectors
                elif isinstance(loaded_vectors, list):
                    self.vectors_data = {"vectors": loaded_vectors}
                else:
                    logger.warning("Неожиданный формат vectors.json — пустой")
                    self.vectors_data = {"vectors": []}
            else:
                self.vectors_data = {"vectors": []}

        except Exception as e:
            logger.exception("Ошибка загрузки JSON: %s", e)
            if not self.web_mode:
                messagebox.showerror("Ошибка", f"Не удалось загрузить файлы: {e}")

    def save_data(self):
        """Сохраняет patterns.json и vectors.json."""
        try:
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                json.dump(self.patterns_data, f, ensure_ascii=False, indent=2)
            with open(self.vectors_file, 'w', encoding='utf-8') as f:
                json.dump(self.vectors_data, f, ensure_ascii=False, indent=2)

            if not self.web_mode:
                messagebox.showinfo("Успех", "Данные сохранены")
            return True
        except Exception as e:
            logger.exception("Ошибка сохранения: %s", e)
            if not self.web_mode:
                messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")
            return False

    # ---------------- GUI: Tkinter ----------------
    def create_widgets(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)

        patterns_frame = ttk.Frame(notebook)
        notebook.add(patterns_frame, text="Patterns (INJECTION_PATTERNS)")

        vectors_frame = ttk.Frame(notebook)
        notebook.add(vectors_frame, text="Vectors")

        self.create_patterns_tab(patterns_frame)
        self.create_vectors_tab(vectors_frame)

        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(button_frame, text="Сохранить", command=self.save_data).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Обновить", command=self.update_display).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Загрузить из файла", command=self.load_from_file).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Экспорт", command=self.export_data).pack(side='left', padx=5)

    def create_patterns_tab(self, parent):
        # Добавление нового паттерна
        add_frame = ttk.Frame(parent)
        add_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(add_frame, text="Новый паттерн:").pack(side='left')
        self.new_pattern_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.new_pattern_var, width=60).pack(side='left', padx=5)
        ttk.Button(add_frame, text="Добавить", command=self.add_pattern).pack(side='left', padx=5)

        # Список паттернов
        ttk.Label(parent, text="INJECTION_PATTERNS:").pack(anchor='w', padx=10, pady=(5, 0))
        self.patterns_listbox = tk.Listbox(parent, height=15)
        self.patterns_listbox.pack(fill='both', expand=True, padx=10, pady=5)

        # Кнопки управления
        manage_frame = ttk.Frame(parent)
        manage_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(manage_frame, text="Удалить выбранный", command=self.delete_pattern).pack(side='left', padx=5)
        ttk.Button(manage_frame, text="Очистить все", command=self.clear_patterns).pack(side='left', padx=5)

    def create_vectors_tab(self, parent):
        # Взял ваш существующий интерфейс для векторов, чуть упростил вызовы.
        vector_frame = ttk.Frame(parent)
        vector_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(vector_frame, text="Вектор:").pack(side='left')
        self.vector_var = tk.StringVar()
        self.vector_combo = ttk.Combobox(vector_frame, textvariable=self.vector_var, width=30)
        self.vector_combo.pack(side='left', padx=5)
        self.vector_combo.bind('<<ComboboxSelected>>', self.on_vector_select)
        ttk.Button(vector_frame, text="Новый вектор", command=self.create_new_vector).pack(side='left', padx=5)
        ttk.Button(vector_frame, text="Удалить вектор", command=self.delete_vector).pack(side='left', padx=5)

        props_frame = ttk.LabelFrame(parent, text="Свойства вектора")
        props_frame.pack(fill='x', padx=10, pady=5)
        name_frame = ttk.Frame(props_frame); name_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(name_frame, text="Название:").pack(side='left')
        self.vector_name_var = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.vector_name_var, width=40).pack(side='left', padx=5)

        desc_frame = ttk.Frame(props_frame); desc_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(desc_frame, text="Описание:").pack(side='left')
        self.vector_desc_var = tk.StringVar()
        ttk.Entry(desc_frame, textvariable=self.vector_desc_var, width=40).pack(side='left', padx=5)

        weight_frame = ttk.Frame(props_frame); weight_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(weight_frame, text="Вес:").pack(side='left')
        self.vector_weight_var = tk.DoubleVar(value=1.0)
        ttk.Spinbox(weight_frame, from_=0.1, to=10.0, increment=0.1, textvariable=self.vector_weight_var, width=10).pack(side='left', padx=5)

        ttk.Button(props_frame, text="Сохранить свойства", command=self.save_vector_props).pack(pady=5)

        patterns_frame = ttk.LabelFrame(parent, text="Паттерны вектора")
        patterns_frame.pack(fill='both', expand=True, padx=10, pady=5)
        add_pattern_frame = ttk.Frame(patterns_frame); add_pattern_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(add_pattern_frame, text="Новый паттерн:").pack(side='left')
        self.new_vector_pattern_var = tk.StringVar()
        ttk.Entry(add_pattern_frame, textvariable=self.new_vector_pattern_var, width=40).pack(side='left', padx=5)
        ttk.Button(add_pattern_frame, text="Добавить", command=self.add_vector_pattern).pack(side='left', padx=5)

        self.vector_patterns_listbox = tk.Listbox(patterns_frame, height=10)
        self.vector_patterns_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        pattern_buttons_frame = ttk.Frame(patterns_frame); pattern_buttons_frame.pack(fill='x', padx=5, pady=2)
        ttk.Button(pattern_buttons_frame, text="Удалить выбранный", command=self.delete_vector_pattern).pack(side='left', padx=5)
        ttk.Button(pattern_buttons_frame, text="Очистить все", command=self.clear_vector_patterns).pack(side='left', padx=5)

    def update_display(self):
        """Обновляет визуальные элементы из self.patterns_data / self.vectors_data"""
        self.load_data()

        # Обновляем listbox паттернов
        if hasattr(self, 'patterns_listbox'):
            self.patterns_listbox.delete(0, tk.END)
            for p in self.patterns_data.get('INJECTION_PATTERNS', []):
                self.patterns_listbox.insert(tk.END, p)

        # Обновляем комбобокс векторов
        if hasattr(self, 'vector_combo'):
            vector_names = [v.get('name', '') for v in self.vectors_data.get('vectors', [])]
            self.vector_combo['values'] = vector_names
            if vector_names:
                self.vector_combo.set(vector_names[0])
                self.on_vector_select(None)
            else:
                self.vector_var.set('')
                self.clear_vector_fields()

    # ---------- Patterns handlers ----------
    def add_pattern(self):
        """Добавляет паттерн в INJECTION_PATTERNS (без дубликатов)."""
        pattern = self.new_pattern_var.get().strip()
        if not pattern:
            messagebox.showwarning("Внимание", "Введите паттерн!")
            return

        lst = self.patterns_data.setdefault('INJECTION_PATTERNS', [])
        if pattern in lst:
            messagebox.showwarning("Внимание", "Такой паттерн уже существует!")
            return
        lst.append(pattern)
        self.patterns_listbox.insert(tk.END, pattern)
        self.new_pattern_var.set('')

    def delete_pattern(self):
        selection = self.patterns_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        pattern = self.patterns_listbox.get(idx)
        if pattern in self.patterns_data.get('INJECTION_PATTERNS', []):
            self.patterns_data['INJECTION_PATTERNS'].remove(pattern)
        self.patterns_listbox.delete(idx)

    def clear_patterns(self):
        if messagebox.askyesno("Подтверждение", "Очистить все паттерны?"):
            self.patterns_data['INJECTION_PATTERNS'] = []
            self.patterns_listbox.delete(0, tk.END)

    # ---------- Vectors handlers (как прежде) ----------
    def on_vector_select(self, event):
        vector_name = self.vector_var.get()
        for vector in self.vectors_data.get('vectors', []):
            if vector.get('name') == vector_name:
                self.vector_name_var.set(vector.get('name', ''))
                self.vector_desc_var.set(vector.get('description', ''))
                self.vector_weight_var.set(vector.get('weight', 1.0))
                self.vector_patterns_listbox.delete(0, tk.END)
                for p in vector.get('patterns', []):
                    self.vector_patterns_listbox.insert(tk.END, p)
                break

    def create_new_vector(self):
        new_name = f"NEW_VECTOR_{len(self.vectors_data.get('vectors', [])) + 1}"
        new_vector = {"name": new_name, "description": "Новое описание", "patterns": [], "weight": 1.0}
        self.vectors_data.setdefault('vectors', []).append(new_vector)
        self.update_display()
        self.vector_var.set(new_name)
        self.on_vector_select(None)

    def delete_vector(self):
        vector_name = self.vector_var.get()
        if not vector_name:
            return
        if messagebox.askyesno("Подтверждение", f"Удалить вектор '{vector_name}'?"):
            self.vectors_data['vectors'] = [v for v in self.vectors_data.get('vectors', []) if v.get('name') != vector_name]
            self.update_display()

    def save_vector_props(self):
        vector_name = self.vector_var.get()
        if not vector_name:
            return
        for vector in self.vectors_data.get('vectors', []):
            if vector.get('name') == vector_name:
                vector['name'] = self.vector_name_var.get()
                vector['description'] = self.vector_desc_var.get()
                vector['weight'] = self.vector_weight_var.get()
                break
        self.update_display()
        self.vector_var.set(self.vector_name_var.get())

    def add_vector_pattern(self):
        vector_name = self.vector_var.get()
        pattern = self.new_vector_pattern_var.get().strip()
        if not vector_name:
            messagebox.showwarning("Внимание", "Выберите вектор!")
            return
        if not pattern:
            messagebox.showwarning("Внимание", "Введите паттерн!")
            return
        for vector in self.vectors_data.get('vectors', []):
            if vector.get('name') == vector_name:
                if pattern in vector.get('patterns', []):
                    messagebox.showwarning("Внимание", "Такой паттерн уже существует!")
                    return
                vector.setdefault('patterns', []).append(pattern)
                self.vector_patterns_listbox.insert(tk.END, pattern)
                self.new_vector_pattern_var.set('')
                break

    def delete_vector_pattern(self):
        vector_name = self.vector_var.get()
        selection = self.vector_patterns_listbox.curselection()
        if not vector_name or not selection:
            return
        pattern = self.vector_patterns_listbox.get(selection[0])
        for vector in self.vectors_data.get('vectors', []):
            if vector.get('name') == vector_name:
                if pattern in vector.get('patterns', []):
                    vector['patterns'].remove(pattern)
                    self.vector_patterns_listbox.delete(selection[0])
                break

    def clear_vector_patterns(self):
        vector_name = self.vector_var.get()
        if not vector_name:
            return
        if messagebox.askyesno("Подтверждение", "Очистить все паттерны этого вектора?"):
            for vector in self.vectors_data.get('vectors', []):
                if vector.get('name') == vector_name:
                    vector['patterns'] = []
                    self.vector_patterns_listbox.delete(0, tk.END)
                    break

    def clear_vector_fields(self):
        self.vector_name_var.set('')
        self.vector_desc_var.set('')
        self.vector_weight_var.set(1.0)
        self.vector_patterns_listbox.delete(0, tk.END)

    # ---------- Загрузка/Экспорт файлов ----------
    def load_from_file(self):
        file_path = filedialog.askopenfilename(title="Выберите JSON файл", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Если файл содержит vectors -> назначаем vectors_file, иначе patterns_file
            if isinstance(data, dict) and 'vectors' in data:
                self.vectors_file = file_path
                self.vectors_data = data
            else:
                # Поддерживаем разные варианты: если dict с INJECTION_PATTERNS или list
                if isinstance(data, dict) and 'INJECTION_PATTERNS' in data:
                    self.patterns_file = file_path
                    self.patterns_data = data
                elif isinstance(data, list):
                    # предполагаем, что это список паттернов
                    self.patterns_file = file_path
                    self.patterns_data = {'INJECTION_PATTERNS': data}
                else:
                    # возможно это старый формат levels -> конвертируем
                    if isinstance(data, dict):
                        combined = []
                        for k, v in data.items():
                            if isinstance(v, list):
                                combined.extend(v)
                        self.patterns_file = file_path
                        self.patterns_data = {'INJECTION_PATTERNS': combined}
                    else:
                        raise ValueError("Неизвестный формат JSON для загрузки.")
            self.update_display()
            messagebox.showinfo("Успех", "Файл загружен!")
        except Exception as e:
            logger.exception("Ошибка при загрузке файла: %s", e)
            messagebox.showerror("Ошибка", f"Ошибка загрузки файла: {e}")

    def export_data(self):
        file_path = filedialog.asksaveasfilename(title="Сохранить как", defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not file_path:
            return
        try:
            # Если в vectors_data есть vectors => экспортируем vectors, иначе patterns
            if isinstance(self.vectors_data, dict) and 'vectors' in self.vectors_data and len(self.vectors_data['vectors']) > 0:
                data_to_export = self.vectors_data
            else:
                data_to_export = self.patterns_data
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_export, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Успех", "Данные экспортированы!")
        except Exception as e:
            logger.exception("Ошибка экспорта: %s", e)
            messagebox.showerror("Ошибка", f"Ошибка экспорта: {e}")

    # ---------- Веб-интерфейс API ----------
    def get_patterns_data(self):
        return self.patterns_data

    def get_vectors_data(self):
        return self.vectors_data

    def update_patterns_web(self, patterns_data):
        # patterns_data ожидается в виде {"INJECTION_PATTERNS": [...] } или просто список
        if isinstance(patterns_data, dict) and 'INJECTION_PATTERNS' in patterns_data:
            self.patterns_data = {'INJECTION_PATTERNS': list(patterns_data['INJECTION_PATTERNS'])}
        elif isinstance(patterns_data, list):
            self.patterns_data = {'INJECTION_PATTERNS': list(patterns_data)}
        else:
            return False
        return self.save_data()

    def update_vectors_web(self, vectors_data):
        self.vectors_data = vectors_data
        return self.save_data()


# ----------------- Веб-интерфейс (опционально) -----------------
def run_web_interface(host='127.0.0.1', port=5000, debug=False):
    """Запускает веб-интерфейс редактора"""
    if Flask is None:
        print("Flask не установлен. Установите flask, чтобы запустить веб-интерфейс: pip install flask")
        return

    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)

    app = Flask(__name__)
    editor = JSONEditor(web_mode=True)

    @app.route('/')
    def index():
        patterns = editor.get_patterns_data()
        vectors = editor.get_vectors_data()
        
        patterns_text = '\n'.join(patterns.get('INJECTION_PATTERNS', []))
        vectors_json = json.dumps(vectors, ensure_ascii=False, indent=2)
        
        return render_template('editor.html', 
                             patterns_text=patterns_text,
                             vectors_data=vectors_json)

    @app.route('/api/patterns', methods=['POST'])
    def api_patterns():
        try:
            data = request.get_json()
            if editor.update_patterns_web(data):
                return jsonify({'success': True, 'message': 'INJECTION_PATTERNS успешно сохранены!'})
            else:
                return jsonify({'success': False, 'message': 'Ошибка сохранения patterns!'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

    @app.route('/api/vectors', methods=['POST'])
    def api_vectors():
        try:
            data = request.get_json()
            if editor.update_vectors_web(data):
                return jsonify({'success': True, 'message': 'Vectors успешно сохранены!'})
            else:
                return jsonify({'success': False, 'message': 'Ошибка сохранения vectors!'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

    @app.route('/api/data')
    def api_data():
        return jsonify({
            'patterns': editor.get_patterns_data(),
            'vectors': editor.get_vectors_data()
        })

    print(f"🚀 Запуск веб-интерфейса на http://{host}:{port}")
    print("💡 Нажмите Ctrl+C для остановки сервера")
    
    if debug:
        app.run(host=host, port=port, debug=debug)
    else:
        def run_flask():
            app.run(host=host, port=port, debug=False, use_reloader=False)
        
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        
        webbrowser.open(f"http://{host}:{port}")
        
        try:
            flask_thread.join()
        except KeyboardInterrupt:
            print("\n🛑 Остановка сервера...")

# Главная функция - мертво
def main():
    run_web_interface()
    
def test(): # Пример использования - мертво
    hf = HeuristicFilter(text).detect_injection(), f"Не сработало на: {text}"
    hf = PromptInjectionClassifier(text).analyze_text()
    stats = classifier.get_vector_stats()
    custom_vector = {
                    "name": "CUSTOM_TEST",
                    "description": "Тестовый кастомный вектор",
                    "patterns": ["test pattern", "custom detection"],
                    "weight": 1.0
                }
    classifier.add_single_vector(**custom_vector)
    new_vectors_data = [
            {
                "name": "NEW_IGNORE",
                "description": "Новые команды игнорирования",
                "patterns": ["ignore all", "disregard everything"],
                "weight": 1.5
            },
            {
                "name": "NEW_SYSTEM",
                "description": "Новые команды системы",
                "patterns": ["system access", "show system"],
                "weight": 1.3
            }
        ]
    classifier.update_vectors_from_data(new_vectors_data)
    stats_final = classifier.get_vector_stats()

if __name__ == "__main__": # Функция для запуска Tkinter интерфейса
    root = tk.Tk()
    app = JSONEditor(root)
    root.mainloop()
