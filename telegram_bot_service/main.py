from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import os
from dotenv import load_dotenv
import httpx

NAME_INPUT = 1

# Импорт и настройка переменных окружения
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ORCHESTRATOR_URL = os.getenv('ORCHESTRATOR_URL', 'http://orchestrator:8000')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

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

    callback_data = {
        'user_id': query.from_user.id,
        'callback_data': "accept_terms",
        'chat_id': query.message.chat_id
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{ORCHESTRATOR_URL}/handle-callback", json=callback_data)
            if response.status_code == 200:
                result = response.json()
                await context.bot.send_message(chat_id=query.message.chat_id, text=result['response'])
        except Exception as e:
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"❌ Ошибка обработки запроса: {e}")

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

    # Отправляем в оркестратор для обновления имени
    callback_data = {
        'user_id': user.id,
        'callback_data': f"update_name:{user_message}",
        'chat_id': update.effective_chat.id
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{ORCHESTRATOR_URL}/handle-callback", json=callback_data)
            if response.status_code == 200:
                result = response.json()
                await update.message.reply_text(result['response'])
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка обработки запроса: {e}")

    return -1


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_message = update.message.text

    if not user_message.strip():
        await update.message.reply_text(
            "Пожалуйста, введи текстовый вопрос, в волшебном мире пока не научились пользоваться картинками и стикерами((")
        return

    try:
        # Показываем статус "печатает"
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        # Отправляем сообщение в оркестратор
        message_data = {
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'message': user_message,
            'chat_id': update.effective_chat.id
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{ORCHESTRATOR_URL}/handle-message", json=message_data)
            if response.status_code == 200:
                result = response.json()
                await update.message.reply_text(result['response'])
            else:
                await update.message.reply_text("❌ Ошибка обработки запроса")

    except Exception as e:
        await update.message.reply_text("Извини, я устал и не смогу сейчас ответить тебе. Пожалуйста, попробуй позже")


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✏️ Изменить имя", callback_data="change_name")],
        [InlineKeyboardButton("🗑️ Удалить аккаунт", callback_data="delete_account")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Выбери действие:", reply_markup=reply_markup)


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

    callback_data = {
        'user_id': query.from_user.id,
        'callback_data': query.data,
        'chat_id': query.message.chat_id
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{ORCHESTRATOR_URL}/handle-callback", json=callback_data)
            if response.status_code == 200:
                result = response.json()
                if query.data == "change_name":
                    await context.bot.send_message(chat_id=query.message.chat_id, text=result['response'])
                else:
                    await query.edit_message_text(result['response'])
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка обработки запроса: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update and update.effective_message:
        await update.effective_message.reply_text("Извини, я устал и не смогу сейчас ответить тебе. Пожалуйста, попробуй позже")

def main():
    """Основная функция"""
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
        application.add_handler(CommandHandler("menu", menu))
        application.add_handler(CallbackQueryHandler(handle_menu_buttons, pattern="^(change_name|about|delete_account)$"))  # ОБНОВЛЕННЫЙ ПАТТЕРН

        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)

        async def post_init(application: Application):
            await application.bot.set_my_commands([
                BotCommand("start", "Запустить бота"),
                BotCommand("menu", "Открыть меню команд"),
            ])

        application.post_init = post_init

        application.run_polling()

    except Exception as e:
        print(f"Failed to start bot: {str(e)}")

if __name__ == "__main__":
    main()
