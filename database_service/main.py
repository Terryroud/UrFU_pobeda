from fastapi import FastAPI, HTTPException
from database import TelegramDatabase
from pydantic import BaseModel
from typing import Optional, List
import os

app = FastAPI(title="Database Service")

# Инициализация базы данных
db = TelegramDatabase(db_name=os.getenv('DATABASE_NAME', 'telegram_bot.db'))


# Модели данных
class UserCreate(BaseModel):
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class MessageCreate(BaseModel):
    user_id: int
    user_message: str
    bot_response: str


class UserResponse(BaseModel):
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    custom_name: Optional[str]
    created_at: str


@app.post("/users")
async def create_or_update_user(user: UserCreate):
    """Создание или обновление пользователя"""
    try:
        db.add_user(
            user_id=user.user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        return {"status": "success", "message": "User created/updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Получение информации о пользователе"""
    try:
        user_data = db.get_user(user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "user_id": user_data['user_id'],
            "username": user_data['username'],
            "first_name": user_data['first_name'],
            "last_name": user_data['last_name'],
            "user_name": db.get_user_name(user_id),  # Имя для обращения
            "custom_name": user_data['custom_name'],
            "created_at": user_data['created_at']
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/users/{user_id}/name")
async def update_user_name(user_id: int, name: str):
    """Обновление имени пользователя"""
    try:
        db.update_user_name(user_id, name)
        return {"status": "success", "message": "Name updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/messages")
async def add_message(message: MessageCreate):
    """Добавление сообщения в историю"""
    try:
        db.add_message(message.user_id, message.user_message, message.bot_response)
        return {"status": "success", "message": "Message added"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation-history/{user_id}")
async def get_conversation_history(user_id: int, limit: int = 50):
    """Получение истории переписки"""
    try:
        history = db.get_conversation_history(user_id, limit)
        messages = db.get_recent_messages(user_id, limit)

        return {
            "user_id": user_id,
            "history": history,
            "messages": messages,
            "message_count": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}/stats")
async def get_user_stats(user_id: int):
    """Получение статистики пользователя"""
    try:
        stats = db.get_user_stats(user_id)
        return {
            "user_id": user_id,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/users/{user_id}")
async def delete_user_data(user_id: int):
    """Удаление данных пользователя"""
    try:
        db.delete_user_data(user_id)
        return {"status": "success", "message": "User data deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cleanup")
async def cleanup_old_messages(days: int = 30):
    """Очистка старых сообщений"""
    try:
        db.cleanup_old_messages(days)
        return {"status": "success", "message": f"Cleaned up messages older than {days} days"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    try:
        # Простая проверка подключения к БД
        db.get_user(1)  # Пытаемся выполнить простой запрос
        return {"status": "healthy", "service": "database"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)