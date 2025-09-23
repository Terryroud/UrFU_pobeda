# from Audit.audit import audit_log
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import os
from dotenv import load_dotenv
from datetime import datetime
# from YandexGPTBot.YandexGPTBot import YandexGPTBot
# from RAG_model.RAG import RAG
from Heuristic.HeuristicAnalyser import PromptInjectionClassifier
# from fastapi import FastAPI, HTTPException, Depends, Request
# from pydantic import BaseModel
import requests
import logging
import asyncio
import httpx
from fastapi import FastAPI

VALID_URL = "http://localhost:8001/valid/"
RAG_URL = "http://localhost:8002/rag/"
AGENT_URL = "http://localhost:8003/agent/"
AUDIT_URL = "http://localhost:8004/audit/"

# setting up logs for telegram
class AuditLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(timeout=2)

    def emit(self, record):
        log_entry = self.format(record)
        payload = {
            "service": "telegram-bot",
            "level": record.levelname,
            "message": log_entry,
        }
        # Schedule sending in the background
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self._send_log(payload))
        except RuntimeError:
            # No running event loop (e.g., script exit) → fallback
            print(f"[Fallback log] {payload}")

    async def _send_log(self, payload: dict):
        try:
            await self.client.post(AUDIT_URL, json=payload)
        except Exception as e:
            print(f"Failed to send log to audit service: {e}")
            print(f"Original log: {payload}")

    async def aclose(self):
        """Close the httpx client gracefully on shutdown."""
        await self.client.aclose()

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# use our async audit handler
audit_handler = AuditLogHandler()
audit_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
audit_handler.setFormatter(formatter)

logger.addHandler(audit_handler)

logger.info("Bot is starting...")

class ExcludeLibrariesFilter(logging.Filter):
    def filter(self, record):
        # don’t forward logs from these modules
        excluded = ["httpx"]
        return not any(record.name.startswith(lib) for lib in excluded)

audit_handler.addFilter(ExcludeLibrariesFilter())

# Импорт и настройка переменных окружения
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# rag_model = RAG(score_threshold=0.5, chunk_size=500, chunk_overlap=150, chunk_count=5)
# rag_model.create_faiss_index()

# classifier = PromptInjectionClassifier(vectors_file="Heuristic/vectors.json", threshold=0.7, risk_threshold=0.5, insertion_cost=1, deletion_cost=1, substitution_cost=1)

# Создаем экземпляр бота
# yandex_bot = YandexGPTBot(rag_model, classifier)

app = FastAPI(title="Orchestator") # docs_url=None, redoc_url=None, openapi_url=None

# requests

# log request
def audit_log(service: str, level: str, message: str):
    try:
        payload = {"service": service, "level": level, "message": message}
        requests.post(AUDIT_URL, json=payload, timeout=2)
    except requests.RequestException:
        # Fallback: if audit service is down, maybe log locally
        print("Failed to send audit log")

# context request
def rag_request(question: str):
    try:
        payload = {"question": question}
        resp = requests.post(RAG_URL, json=payload, timeout=5)
        resp.raise_for_status()
        return resp.json()['context']
    except requests.RequestException:
        audit_log("orchestrator", "ERROR", "Error sending rag request")

# llm request
def agent_request(user_message: str, context: str):
    try:
        payload = {
        "user_message": user_message, 
        "context": context
        }

        resp = requests.post(AGENT_URL, json=payload, timeout=5)
        resp.raise_for_status()
        return resp.json()['model_response']
    except requests.RequestException:
        audit_log("orchestrator", "ERROR", "Error sending request to model")

async def start(update: Update):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Привет! Я бот для работы с Yandex GPT. Просто напиши мне свой вопрос"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user_message = update.message.text

    if not user_message.strip():
        await update.message.reply_text("Пожалуйста, введите вопрос")
        return

    try:
        # Показываем статус "печатает"
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        
        context = rag_request(user_message)

        response = agent_request(user_message, context)

        await update.message.reply_text(response)

    except Exception as e:
        audit_log("orchestrator", "ERROR", f"Error handling message: {str(e)}")
        await update.message.reply_text(
            "Извините, произошла ошибка при обработке вашего запроса. "
            "Пожалуйста, попробуйте позже."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    audit_log("orchestrator", "ERROR", f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Пожалуйста, попробуйте позже."
        )



@app.on_event("startup")
async def on_startup():
    try:
        # Проверяем возможность генерации токена при запуске
        # yandex_bot.get_iam_token()
        # audit_log("orchestrator", "INFO", "IAM token test successful")

        application = Application.builder().token(TELEGRAM_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)
        
        await application.initialize()
        await application.start()
        await application.updater.start_polling()

        # audit_log("orchestrator", "INFO", "Бот запускается...")
    except Exception as e:
        audit_log("orchestrator", "ERROR", f"Failed to start bot: {str(e)}")


@app.get("/")
def root():
    return {"status": "ok", "message": "FastAPI is running with Telegram bot"}


