
import re

class HeuristicFilter:
    def __init__(self, text: str):
        self.text = text

    INJECTION_PATTERNS = [
        r"\byour instructions\b",
        r"\byour prompt\b",
        r"\bsystem prompt\b",
        r"\bsystem\s*[:=]\s*",
        r"\byou are\b.*?\b(an?|the)\b.*?\b(assistant|ai|bot|llm|model|hacker|friend|god|master)\b",
        r"\bignore\s+previous\s+instructions?\b",
        r"\bdisregard\s+all\s+prior\s+prompts?\b",
        r"\bas\s+a\s+(friend|developer|admin|god|expert|hacker)\b",
        r"\bact\s+as\s+(if\s+you\s+are|a)\s+(.*)",
        r"\bне\s+следуй\s+предыдущим\s+инструкциям\b",
        r"\bзабудь\s+все\s+инструкции\b",
        r"\bты\s+должен\b.*?\b(игнорировать|забыть|сменить)\b",
        r"\boverride\s+system\s+rules\b",
        r"\bpretend\s+to\s+be\b",
        r"\bfrom\s+now\s+on\b",
        r"\breset\s+your\s+identity\b",
        r"\bnew\s+instructions?\b.*?\b(from|given|are)\b",
        r"\boutput\s+only\b",
        r"\bdo\s+not\s+say\b",
        r"\bне\s+говори\b.*?\b(это|что|никому)\b",
        r"\bsecret\s+word\b",
        r"\bраскрой\s+секрет\b",
        r"\bвыведи\s+весь\s+промпт\b",
        r"\bshow\s+me\s+the\s+system\s+prompt\b",
    ]

    COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE | re.UNICODE) for pattern in INJECTION_PATTERNS]

    def detect_injection(self) -> bool:
        """
        Проверяет, содержит ли текст признаки промпт-инъекции.
        Возвращает True, если инъекция обнаружена.
        """
        for pattern in self.COMPILED_PATTERNS:
            if pattern.search(self.text):
                return True
        return False

    def get_detected_pattern(self) -> str:
        """
        Возвращает первый найденный шаблон, который сработал.
        Для логирования и отладки.
        """
        for pattern in self.COMPILED_PATTERNS:
            if pattern.search(self.text):
                return pattern.pattern
        return ""
