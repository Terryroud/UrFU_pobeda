from database import TelegramDatabase
from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel

db = TelegramDatabase()

app = FastAPI(title="DB", docs_url=None, redoc_url=None, openapi_url=None)

class NewUser(BaseModel):
    user_id: int
    username: str
    first_name: str
    last_name: str

class UpdateUsername(BaseModel):
    user_id: int
    username: str

class GetUser(BaseModel):
    user_id: int

class NewMessage(BaseModel):
    user_id: int
    message_text: str
    bot_response: str

class GetRecentMes(BaseModel):
    user_id: int
    limit: int


@app.post("/database/add_user")
async def add_user(new_user: NewUser, request: Request):
    db.add_user(
        user_id=new_user.user_id,
        username=new_user.username,
        first_name=new_user.first_name,
        last_name=new_user.last_name
    )

    return {"status": "ok"}

@app.get('/database/get_user_name/{user_id}')
async def get_user_name(user_id: int, request: Request):
    user_name = db.get_user_name(user_id)

    return {"user_name": user_name}

@app.patch("/database/update_user_name")
async def update_user_name(new_name: UpdateUsername, request: Request):
    db.update_user_name(new_name.user_id, new_name.username)

    return {"status": "ok"}

@app.delete('/database/delete_user/{user_id}')
async def delete_user(user_id: int):
    db.delete_user_data(user_id)
    return {"status": "ok"}

@app.get('/database/get_history/{user_id}')
async def get_history(user_id: int, limit: int = 50):
    chat_history = db.get_conversation_history(user_id, limit)
    response = {
    "history": chat_history
    }

    return response

@app.post('/database/add_message/')
async def add_message(message: NewMessage, request: Request):
    db.add_message(message.user_id, message.message_text, message.bot_response)

    return {"status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
