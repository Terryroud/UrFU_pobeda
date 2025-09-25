# 🧙‍♂️ Harry Potter Telegram Bot

Telegram бот, имитирующий общение с Гарри Поттером (на основе LLM YandexGPT и RAG системы с лором персонажа), построенный на микросервисной архитектуре с использованием FastAPI и Docker.

## 🏗️ Архитектура проекта

Проект использует микросервисную архитектуру с центральным оркестратором:

```
Telegram Bot → Orchestrator → [RAG, AI, Security, Database, Audit Services]
```

### 📦 Микросервисы

| Сервис | Порт | Назначение |
|--------|------|------------|
| **orchestrator** | 8000 | Центральный координатор запросов |
| **telegram-bot** | - | Прием сообщений от Telegram |
| **rag-service** | 8001 | RAG модель и семантический поиск |
| **ai-service** | 8002 | Yandex GPT генерация |
| **heuristic-service** | 8003 | Анализ безопасности сообщений |
| **database-service** | 8004 | Управление базой данных |
| **audit-service** | 8005 | Централизованное логирование |

## 🚀 Быстрый старт

### Предварительные требования

- Docker & Docker Compose
- Python 3.11+
- Telegram Bot Token
- Yandex Cloud API ключи

### 1. Клонирование и настройка

```bash
git clone <repository-url>
cd UrFU_pobeda
```

### 2. Настройка переменных окружения

Создайте файл `.env` на основе `.env.example`:

```env
# Telegram
TELEGRAM_TOKEN=your_telegram_bot_token_here

# Yandex Cloud
YANDEX_API_KEY=your_yandex_api_key
IAM_TOKEN=your_iam_token
FOLDER_ID=your_folder_id
KEY_ID=your_key_id
SERVICE_ACCOUNT_ID=your_service_account_id

# База данных
DATABASE_URL=sqlite:///app/data/bot_database.db
```

### 3. Запуск в Docker

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Проверка статуса
docker-compose ps

# Остановка всех сервисов
docker-compose down
```

### 4. Проверка работоспособности

```bash
# Проверка здоровья сервисов
curl http://localhost:8000/health  # orchestrator
curl http://localhost:8001/health  # rag-service
curl http://localhost:8002/health  # ai-service
curl http://localhost:8003/health  # security
curl http://localhost:8004/health  # database
curl http://localhost:8005/health  # audit
```

## 🎯 Функциональность

### Основные возможности

- **💬 Интеллектуальный чат** - общение с AI в стиле Гарри Поттера
- **📚 Контекстный поиск** - RAG модель для точных ответов от лица персонажа
- **🛡️ Безопасность** - эвристический анализ сообщений для отсеивания вредоносных запросов
- **💾 История диалогов** - сохранение контекста беседы в рамках одной сессии
- **👤 Управление профилем** - персонализация общения

### Команды бота

- `/start` - начать работу с ботом
- `/menu` - открыть меню команд
- `/change_name` - изменить имя пользователя
- `/delete_account` - удалить аккаунт 

## 🔧 Разработка

### Локальная разработка

```bash
# Установка зависимостей
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или .venv\Scripts\activate  # Windows

pip install -r requirements.txt

# Запуск конкретного сервиса
cd orchestrator_service
python main.py
```

### Структура проекта

```
UrFU_pobeda/
├── orchestrator_service/     # Центральный оркестратор
├── telegram_bot_service/     # Telegram бот
├── rag_service/             # RAG модель
├── ai_service/              # Yandex GPT
├── heuristic_service/       # Анализ безопасности
├── database_service/        # База данных
├── audit_service/           # Логирование
├── docker-compose.yml       # Docker конфигурация
└── README.md               # Документация
```


## 🛠️ Технологический стек

### Backend
- **FastAPI** - асинхронные API
- **Docker** - контейнеризация
- **SQLite** - база данных (с возможностью миграции на PostgreSQL)
- **FAISS** - векторный поиск

### AI/ML
- **Yandex GPT** - генерация ответов
- **Sentence Transformers** - эмбеддинги
- **RAG** - Retrieval-Augmented Generation

### Инфраструктура
- **Docker Compose** - оркестрация
- **Yandex Cloud** - хостинг
- **GitLab CI/CD** - автоматизация деплоя


## 📄 Лицензия

Проект разработан в образовательных целях. Все права на образы Гарри Поттера принадлежат правообладателям.

---

**Примечание**: Для работы бота необходим действующий Telegram Bot Token и доступ к Yandex Cloud API.
