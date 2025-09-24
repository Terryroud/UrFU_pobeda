from fastapi import FastAPI, HTTPException
import httpx
import os
from pydantic import BaseModel

app = FastAPI(title="Orchestrator Service")

# Конфигурация сервисов
SERVICES = {
    'rag': os.getenv('RAG_URL', 'http://rag_service:8001'),
    'ai': os.getenv('AI_URL', 'http://ai_service:8002'),
    'security': os.getenv('SECURITY_URL', 'http://heuristic_service:8003'),
    'database_service': os.getenv('DATABASE_URL', 'http://database_service:8004'),
    'audit_service': os.getenv('AUDIT_URL', 'http://audit_service:8005')
}


class MessageRequest(BaseModel):
    user_id: int
    username: str = None
    first_name: str = None
    last_name: str = None
    message: str
    chat_id: int


class CallbackRequest(BaseModel):
    user_id: int
    callback_data: str
    chat_id: int


class UserData(BaseModel):
    user_id: int
    username: str = None
    first_name: str = None
    last_name: str = None

async def audit_log(service: str, level: str, message: str, user_id: int = None):
    """Отправка лога в audit service через оркестратор"""
    try:
        async with httpx.AsyncClient() as client:
            log_data = {
                "service": service,
                "level": level,
                "message": message,
                "user_id": user_id
            }
            await client.post(f"{SERVICES['audit']}/log", json=log_data, timeout=5)
    except Exception as e:
        # Фолбэк: вывод в консоль если audit service недоступен
        print(f"[FALLBACK {level}] {service}: {message}")

@app.post("/handle-message")
async def handle_message(request: MessageRequest):
    try:
        await audit_log("orchestrator", "INFO", f"Starting message processing", request.user_id)

        async with httpx.AsyncClient() as client:
            # 1. Сохраняем/обновляем пользователя
            user_data = UserData(
                user_id=request.user_id,
                username=request.username,
                first_name=request.first_name,
                last_name=request.last_name
            )
            await client.post(f"{SERVICES['database_service']}/users", json=user_data.dict())
            await audit_log("database", "INFO", f"User updated", request.user_id)

            # 2. Получаем имя пользователя
            user_response = await client.get(f"{SERVICES['database_service']}/users/{request.user_id}")
            user_data = user_response.json()
            user_name = user_data.get('user_name', 'User')

            # 3. Проверяем безопасность сообщения
            safety_response = await client.post(
                f"{SERVICES['security']}/check-safety",
                json={'text': request.message}
            )
            safety_data = safety_response.json()
            await audit_log("security", "INFO", f"Safety check completed", request.user_id)

            if safety_data.get('is_invalid', False):
                await audit_log("security", "WARNING", f"Unsafe message detected: {request.message}", request.user_id)
                return {
                    'response': "Извини, я не могу обсуждать такие темы, иначе дементоры высосут из меня душу(((",
                    'status': 'success'
                }

            # 4. Получаем историю переписки
            history_response = await client.get(
                f"{SERVICES['database_service']}/conversation-history/{request.user_id}",
                params={'limit': 50}
            )
            chat_history = history_response.json().get('history', '')

            # 5. Получаем контекст из RAG
            rag_response = await client.get(
                f"{SERVICES['rag']}/query",
                params={'question': request.message}
            )
            rag_data = rag_response.json()
            await audit_log("rag", "INFO", f"RAG context retrieved", request.user_id)

            # 6. Генерируем ответ через AI
            ai_request = {
                'message': request.message,
                'chat_history': chat_history,
                'user_name': user_name,
                'rag_context': rag_data.get('answer', ''),
                'is_invalid': safety_data.get('is_invalid', False),
                'valid_stat': safety_data.get('valid_stat', {})
            }

            ai_response = await client.post(
                f"{SERVICES['ai']}/generate",
                json=ai_request
            )
            ai_data = ai_response.json()
            response_text = ai_data.get('response', '')
            await audit_log("ai", "INFO", f"Response generated", request.user_id)

            if not response_text:
                response_text = "Извини, я не могу обсуждать такие темы, иначе дементоры высосут из меня душу((("
                await audit_log("ai", "WARNING", "Empty response generated", request.user_id)

            # 7. Сохраняем сообщение в историю
            await client.post(f"{SERVICES['database_service']}/messages", json={
                'user_id': request.user_id,
                'user_message': request.message,
                'bot_response': response_text
            })

            await audit_log("database", "INFO", "Message saved to history", request.user_id)

            await audit_log("orchestrator", "INFO", "Message processing completed", request.user_id)

            return {
                'response': response_text,
                'status': 'success'
            }

    except Exception as e:
        await audit_log("orchestrator", "ERROR", f"Error handling message: {str(e)}", request.user_id)
        return {
            'response': "Извини, я устал и не смогу сейчас ответить тебе. Пожалуйста, попробуй позже",
            'status': 'error'
        }


@app.post("/handle-callback")
async def handle_callback(request: CallbackRequest):
    """Обработка callback кнопок"""
    try:
        await audit_log("orchestrator", "INFO", f"Processing callback: {request.callback_data}", request.user_id)

        async with httpx.AsyncClient() as client:
            if request.callback_data == "delete_account":
                # Удаляем данные пользователя
                await client.delete(f"{SERVICES['database_service']}/users/{request.user_id}")
                response_text = "✅ Все твои данные удалены! История очищена.\n\nЕсли захочешь пообщаться снова - просто напиши мне 😊"
                await audit_log("database", "INFO", "User data deleted", request.user_id)

            elif request.callback_data == "change_name":
                response_text = "Как тебя зовут? Введи новое имя:"

            elif request.callback_data == "about":
                response_text = "Я Гарри Поттер! И у меня есть жена((("

            elif request.callback_data == "accept_terms":
                # Проверяем есть ли имя у пользователя
                user_response = await client.get(f"{SERVICES['database_service']}/users/{request.user_id}")
                user_data = user_response.json()

                if user_data.get('user_name'):
                    response_text = f"С возвращением, {user_data['user_name']}! О чем хочешь поговорить?"
                else:
                    response_text = "Привет! Я Гарри Поттер. Да-да, тот самый)\nДавай познакомимся! Как тебя зовут?"

            else:
                response_text = "✅"

            await audit_log("orchestrator", "INFO", f"Callback processed: {request.callback_data}", request.user_id)

            return {
                'response': response_text,
                'status': 'success'
            }

    except Exception as e:
        await audit_log("orchestrator", "ERROR", f"Error processing callback: {str(e)}")
        return {
            'response': "❌ Ошибка обработки запроса",
            'status': 'error'
        }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "orchestrator"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)