from YandexGPTBot import YandexGPTBot
from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel
from write_log import audit_log

yandex_bot = YandexGPTBot()
yandex_bot.get_iam_token()
audit_log("orchestrator", "INFO", "IAM token test successful")

app = FastAPI(title="Agent", docs_url=None, redoc_url=None, openapi_url=None)

class FullRequest(BaseModel):
	user_message: str
	chat_history: str
	user_name: str
	rag_answer: str
	is_invalid: bool
	valid_stat: float


@app.post("/agent/")
async def agent_request(full_req: FullRequest, request: Request):
	model_response = yandex_bot.ask_gpt(
		full_req.user_message, 
		full_req.chat_history, 
		full_req.user_name, 
		full_req.rag_answer, 
		full_req.is_invalid, 
		full_req.valid_stat
	)

	response = {
	"model_response": model_response
	}

	return response
