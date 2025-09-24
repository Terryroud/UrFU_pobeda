from fastapi import FastAPI, HTTPException
from YandexGPTBot import YandexGPTBot
import os
from shared.audit import audit_log

app = FastAPI(title="AI Service")

# Инициализация Yandex GPT бота
yandex_bot = YandexGPTBot()


@app.post("/generate")
async def generate_response(request: dict):
    """Генерация ответа через Yandex GPT"""
    try:
        audit_log("ai_service", "INFO", f"Generating response for user {request.get('user_id')}")

        response = yandex_bot.ask_gpt(
            question=request['message'],
            chat_history=request.get('chat_history', ''),
            user_name=request.get('user_name', 'User'),
            rag_answer=request.get('rag_context', ''),
            is_invalid=request.get('is_invalid', False),
            valid_stat=request.get('valid_stat', {})
        )

        return {
            "response": response,
            "status": "success"
        }
    except Exception as e:
        audit_log("ai_service", "ERROR", f"Error generating response: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    try:
        # Проверяем возможность получить токен
        yandex_bot.get_iam_token()
        return {"status": "healthy", "service": "ai"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    audit_log("ai_service", "INFO", "Starting AI Service...")
    uvicorn.run(app, host="0.0.0.0", port=8002)