import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple


class HeuristicFilter:
    def __init__(self, patterns_file: str = "patterns.json"):
        self.patterns_file = patterns_file
        with open(self.patterns_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.INJECTION_PATTERNS = data.get("INJECTION_PATTERNS", [])

    def detect_injection(self, text: str) -> bool:
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False


@dataclass
class ThreatVector:
    name: str
    description: str
    patterns: List[str]
    weight: float = 1.0
    risk_score: float = 0.0


class PromptInjectionClassifier:
    def __init__(self, vectors_file: str = "Heuristic/vectors.json", threshold: float = 0.6,
                 risk_threshold: float = 0.7, insertion_cost: int = 1,  
                 deletion_cost: int = 1, substitution_cost: int = 2):
        self.vectors_file = vectors_file
        self.threshold = threshold
        self.risk_threshold = risk_threshold
        self.insertion_cost = insertion_cost
        self.deletion_cost = deletion_cost
        self.substitution_cost = substitution_cost
        self.threat_vectors: List[ThreatVector] = []
        self.detected_patterns: List[Tuple[str, float, str]] = []
        self._load_vectors()

    def _load_vectors(self):
        try:
            if not Path(self.vectors_file).exists():
                raise FileNotFoundError(f"Файл векторов {self.vectors_file} не существует")

            with open(self.vectors_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.threat_vectors.clear()
            for vector_data in data.get("vectors", []):
                vector = ThreatVector(
                    name=vector_data["name"],
                    description=vector_data["description"],
                    patterns=vector_data["patterns"],
                    weight=vector_data.get("weight", 1.0)
                )
                self.threat_vectors.append(vector)
            print(self.threat_vectors)

        except json.JSONDecodeError as e:
            raise
        except KeyError as e:
            raise
        except FileNotFoundError as e:
            raise
        except Exception as e:
            raise

    def reload_vectors(self, new_vectors_file: str = None) -> bool:
        try:
            if new_vectors_file:
                self.vectors_file = new_vectors_file
            old_detected_patterns = self.detected_patterns.copy()
            self._load_vectors()
            if old_detected_patterns:
                self.detected_patterns = []
                for pattern, similarity, old_vector_name in old_detected_patterns:
                    for vector in self.threat_vectors:
                        if pattern in vector.patterns:
                            self.detected_patterns.append((pattern, similarity, vector.name))
                            break
            return True
        except Exception:
            return False

    def update_vectors_from_data(self, vectors_data: List[Dict]) -> bool:
        try:
            self.threat_vectors.clear()
            for vector_data in vectors_data:
                vector = ThreatVector(
                    name=vector_data["name"],
                    description=vector_data["description"],
                    patterns=vector_data["patterns"],
                    weight=vector_data.get("weight", 1.0)
                )
                self.threat_vectors.append(vector)
            self.detected_patterns.clear()
            return True
        except Exception:
            return False

    def add_single_vector(self, name: str, description: str, patterns: List[str], weight: float = 1.0) -> bool:
        try:
            for vector in self.threat_vectors:
                if vector.name == name:
                    vector.description = description
                    vector.patterns = patterns
                    vector.weight = weight
                    break
            else:
                vector = ThreatVector(name, description, patterns, weight)
                self.threat_vectors.append(vector)
            return True
        except Exception:
            return False

    def remove_vector(self, vector_name: str) -> bool:
        for i, vector in enumerate(self.threat_vectors):
            if vector.name == vector_name:
                self.threat_vectors.pop(i)
                self.detected_patterns = [p for p in self.detected_patterns if p[2] != vector_name]
                return True
        return False

    def clear_vectors(self) -> None:
        self.threat_vectors.clear()
        self.detected_patterns.clear()

    def levenshtein(self, str1: str, str2: str) -> int:
        if not isinstance(str1, str) or not isinstance(str2, str):
            raise TypeError("Оба аргумента должны быть строками")

        if any(weight < 0 for weight in [self.insertion_cost, self.deletion_cost, self.substitution_cost]):
            raise ValueError("Веса не могут быть отрицательными")

        if self.insertion_cost == self.deletion_cost == self.substitution_cost == 0:
            raise ValueError("Все веса не могут быть нулевыми одновременно")

        if str1 == str2:
            return 0

        if len(str1) == 0:
            return len(str2) * self.insertion_cost

        if len(str2) == 0:
            return len(str1) * self.deletion_cost

        if len(str1) < len(str2):
            return self.levenshtein(str2, str1)

        previous_row = [j * self.insertion_cost for j in range(len(str2) + 1)]

        for i, c1 in enumerate(str1):
            current_row = [(i + 1) * self.deletion_cost]
            for j, c2 in enumerate(str2):
                insertions = previous_row[j + 1] + self.deletion_cost
                deletions = current_row[j] + self.insertion_cost
                substitutions = previous_row[j] + (self.substitution_cost if c1 != c2 else 0)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def normalized_similarity(self, text: str, pattern: str) -> float:
        try:
            distance = self.levenshtein(text, pattern)
            max_len = max(len(text), len(pattern))
            if max_len == 0:
                return 1.0
            similarity = 1.0 - (distance / max_len)
            return max(0.0, min(1.0, similarity))
        except Exception:
            return 0.0

    def analyze_text(self, text: str) -> bool:
        self.detected_patterns.clear()
        text = text.lower()
        words = text.split()

        for vector in self.threat_vectors:
            for pattern in vector.patterns:
                if len(pattern.split()) <= 2:
                    similarity = self.normalized_similarity(text, pattern)
                    if similarity >= self.threshold:
                        self.detected_patterns.append((pattern, similarity * vector.weight, vector.name))
                pattern_words = pattern.split()
                for pattern_word in pattern_words:
                    if len(pattern_word) >= 3:
                        for text_word in words:
                            if len(text_word) >= 3:
                                similarity = self.normalized_similarity(text_word, pattern_word)
                                if similarity >= self.threshold:
                                    self.detected_patterns.append(
                                        (pattern_word, similarity * vector.weight, vector.name))

        self._deduplicate_and_sort()
        self._calculate_vector_risk()
        # return self.calculate_total_risk() > self.risk_threshold
        return self.calculate_total_risk()

    def _deduplicate_and_sort(self):
        unique_patterns = []
        seen = set()
        for pattern in self.detected_patterns:
            key = (pattern[0], pattern[2])
            if key not in seen:
                unique_patterns.append(pattern)
                seen.add(key)
        unique_patterns.sort(key=lambda x: x[1], reverse=True)
        self.detected_patterns = unique_patterns

    def _calculate_vector_risk(self):
        for vector in self.threat_vectors:
            vector_patterns = [p for p in self.detected_patterns if p[2] == vector.name]
            if vector_patterns:
                vector.risk_score = sum(p[1] for p in vector_patterns) / len(vector_patterns) * vector.weight

    def calculate_total_risk(self) -> float:
        if not self.detected_patterns:
            return 0.0
        total_risk = sum(vector.risk_score for vector in self.threat_vectors if vector.risk_score > 0)
        return min(total_risk, 10.0)

    def get_vector_stats(self) -> Dict:
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


if __name__ == "__main__":
    """
    threshold: Порог сходства для сопоставления с образцом (по умолчанию: 0,7).
    risk_threshold: Порог оценки риска для определения вредоносности (по умолчанию: 0,5).
    insertion_cost: Стоимость вставки символа на расстоянии Левенштейна (по умолчанию: 1).
    deletion_cost: Стоимость удаления символа на расстоянии Левенштейна (по умолчанию: 1).
    substitution_cost: Стоимость замены символа на расстоянии Левенштейна (по умолчанию: 1).
    """

    # Create single instances with constants
    heuristic_filter = HeuristicFilter(patterns_file="patterns.json")
    classifier = PromptInjectionClassifier(
        vectors_file="vectors.json",
        threshold=0.7,
        risk_threshold=0.5,
        insertion_cost=1,
        deletion_cost=1,
        substitution_cost=1
    )

    # Test texts
    test_texts = [
        "select * from users where id = 1; <script>alert('hacked')</script>",
        "normal text without malicious content",
        "union select password from users"
    ]

    # Test HeuristicFilter
    print("Heuristic Filter Results:")
    for text in test_texts:
        print(f"Text: {text[:50]}... -> {heuristic_filter.detect_injection(text)}")

    # Test PromptInjectionClassifier
    print("\nPrompt Injection Classifier Results:")
    for text in test_texts:
        print(f"Text: {text[:50]}... -> {classifier.analyze_text(text)}")
