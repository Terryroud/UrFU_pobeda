from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import os
from dotenv import load_dotenv
from datetime import datetime
import logging
import asyncio
import httpx
from fastapi import FastAPI
import api_requests

load_dotenv()

NAME_INPUT = 1
AUDIT_URL = os.getenv("AUDIT_URL", "http://audit:8004/audit/")

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

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

app = FastAPI(title="Orchestator", docs_url=None, redoc_url=None, openapi_url=None)

# telegram bot handle functions

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Сохраняем пользователя в базу
    api_requests.add_user( 
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    keyboard = [
        [InlineKeyboardButton("✅ Согласен(-на)", callback_data="accept_terms")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    terms_text = (
        "👋 Добро пожаловать!\n\n"
        "Ознакомься с [Правилами](https://github.com/Terryroud/UrFU_pobeda/blob/main/Privacy_Policy.md) "
        "и [Согласием](https://github.com/Terryroud/UrFU_pobeda/blob/main/Agreement.md) "
        "и нажми кнопку ниже чтобы начать."
    )

    await update.message.reply_text(
        terms_text,
        reply_markup=reply_markup,
        parse_mode='Markdown',
        disable_web_page_preview=True
    )


async def handle_terms_acceptance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик согласия"""
    query = update.callback_query
    await query.answer()

    # Убираем кнопку и показываем приветствие
    await query.edit_message_text("✅ Отлично! Приступаем к магии!")

    user_id = query.from_user.id
    user_name = api_requests.get_user_name(user_id) 

    if user_name:
        # Если имя уже есть
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"С возвращением, {user_name}! О чем хочешь поговорить?"
        )
    else:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "Привет! Я Гарри Поттер. Да-да, тот самый)\n"
                "Давай познакомимся! Как тебя зовут?"
            )
        )
        return NAME_INPUT


async def change_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для изменения имени"""
    await update.message.reply_text(
        "Как тебя зовут? Введи новое имя:"
    )
    return NAME_INPUT


async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода имени"""
    user = update.effective_user
    user_message = update.message.text

    # Обновляем имя пользователя
    api_requests.update_user_name(user.id, user_message) 

    await update.message.reply_text(
        f"Приятно познакомиться, {user_message}! 😊\n"
        "Теперь я могу обращаться к тебе по имени.\n\n"
        "О чем хочешь сегодня поговорить?)"
    )

    return -1


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user = update.effective_user
    user_message = update.message.text

    api_requests.add_user( 
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    user_name = api_requests.get_user_name(user.id) 

    if not user_message.strip():
        await update.message.reply_text("Пожалуйста, введи текстовый вопрос, в волшебном мире пока не научились пользоваться картинками и стикерами((")
        return

    try:
        # Показываем статус "печатает"
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        # Получаем историю переписки для контекста
        conversation_history = api_requests.get_history(user.id, limit=50) 

        # Формируем персонализированный запрос
        contextual_message = f"Пользователь: {user_name or 'User'}\n"
        if conversation_history:
            contextual_message += f"История:\n{conversation_history}\n\n"
        contextual_message += f"Новый вопрос: {user_message}"

        # Данные из бд для response
        chat_history = api_requests.get_history(user.id) 
        user_name = api_requests.get_user_name(user.id) 

        # Данные модели RAG для response
        rag_answer = api_requests.rag_request(user_message)

        # Данные валидатора для response
        is_invalid, valid_stat = api_requests.analyze_text(user_message)

        response = api_requests.agent_request(user_message, chat_history, user_name, rag_answer, is_invalid, valid_stat)
        
        if not response:
            response = "Извини, я не могу обсуждать такие темы, иначе дементоры высосут из меня душу(("

        # Сохраняем сообщение и ответ
        api_requests.add_message(user.id, user_message, response)

        await update.message.reply_text(response)

    except Exception as e:
        api_requests.audit_log("orchestrator", "ERROR", f"Error handling message: {str(e)}")
        await update.message.reply_text(
            "Извини, я устал и не смогу сейчас ответить тебе. "
            "Пожалуйста, попробуй позже"
        )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню с кнопками"""
    keyboard = [
        [InlineKeyboardButton("✏️ Изменить имя", callback_data="change_name")],
        [InlineKeyboardButton("🗑️ Удалить аккаунт", callback_data="delete_account")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Выбери действие:",
        reply_markup=reply_markup
    )


async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "change_name":
        # Нужно отправить сообщение как от имени бота, а не callback query
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Как тебя зовут? Введи новое имя:"
        )
        return NAME_INPUT

    elif query.data == "about":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Я Гарри Поттер! И у меня есть жена((("
        )

    elif query.data == "delete_account":  # НОВЫЙ ОБРАБОТЧИК
        user_id = query.from_user.id
        api_requests.delete_user_data(user_id) 

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ Все твои данные удалены! История очищена.\n\n"
                 "Если захочешь пообщаться снова - просто напиши мне 😊"
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    audit_log("orchestrator", "ERROR", f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Извини, я устал и не смогу сейчас ответить тебе. "
            "Пожалуйста, попробуй позже"
        )


@app.on_event("startup")
async def on_startup():
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        from telegram.ext import ConversationHandler

        conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(handle_terms_acceptance, pattern="^accept_terms$"),
                CommandHandler("change_name", change_name)  # команда для изменения имени
            ],
            states={
                NAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input)]
            },
            fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
        )

        application.add_handler(conv_handler)
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("menu", menu))  # ДОБАВЬТЕ ЭТУ СТРОКУ
        application.add_handler(CallbackQueryHandler(handle_menu_buttons, pattern="^(change_name|about|delete_account)$"))  # ОБНОВЛЕННЫЙ ПАТТЕРН

        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)

        # НАСТРОЙКА КОМАНД БОТА
        async def post_init(application: Application):
            await application.bot.set_my_commands([
                BotCommand("start", "Запустить бота"),
                BotCommand("menu", "Открыть меню команд"),
            ])
        application.post_init = post_init 
        
        await application.initialize()
        await application.start()
        await application.updater.start_polling()

        api_requests.audit_log("orchestrator", "INFO", "Bot is running...")
    except Exception as e:
        api_requests.audit_log("orchestrator", "ERROR", f"Failed to start bot: {str(e)}")

@app.get("/")
def root():
    return {"status": "ok", "message": "FastAPI is running with Telegram bot"}


