from audit import audit_log
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import os
from dotenv import load_dotenv
from datetime import datetime
from YandexGPTBot.YandexGPTBot import YandexGPTBot
from RAG_model.RAG import RAG
from Heuristic.HeuristicAnalyser import PromptInjectionClassifier

# Импорт и настройка переменных окружения
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

rag_model = RAG(score_threshold=0.5, chunk_size=500, chunk_overlap=150, chunk_count=5)
rag_model.create_faiss_index()

classifier = PromptInjectionClassifier(
    vectors_file="Heuristic/vectors.json",
    threshold=0.7,
    risk_threshold=0.5,
    insertion_cost=1,
    deletion_cost=1,
    substitution_cost=1
)

# Создаем экземпляр бота
yandex_bot = YandexGPTBot(rag_model, classifier)

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

        response = yandex_bot.ask_gpt(user_message)
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

def main():
    """Основная функция"""
    try:
        # Проверяем возможность генерации токена при запуске
        yandex_bot.get_iam_token()
        audit_log("orchestrator", "INFO", "IAM token test successful")

        application = Application.builder().token(TELEGRAM_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)

        audit_log("orchestrator", "INFO", "Бот запускается...")
        application.run_polling()

    except Exception as e:
        audit_log("orchestrator", "ERROR", f"Failed to start bot: {str(e)}")

if __name__ == "__main__":
    main()
