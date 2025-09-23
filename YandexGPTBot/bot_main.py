from YandexGPTBot import YandexGPTBot
from fastapi import FastAPI, HTTPException, Depends, Request
# from Heuristic.HeuristicAnalyser import PromptInjectionClassifier
from pydantic import BaseModel
import requests
from write_log import audit_log

# classifier = PromptInjectionClassifier(
#     vectors_file="Heuristic/vectors.json",
#     threshold=0.7,
#     risk_threshold=0.5,
#     insertion_cost=1,
#     deletion_cost=1,
#     substitution_cost=1
# )

yandex_bot = YandexGPTBot()
yandex_bot.get_iam_token()
audit_log("orchestrator", "INFO", "IAM token test successful")

app = FastAPI(title="Agent") # docs_url=None, redoc_url=None, openapi_url=None

class FullRequest(BaseModel):
	user_message: str
	context: str


@app.post("/agent/")
async def agent_request(full_req: FullRequest, request: Request):
	model_response = yandex_bot.ask_gpt(full_req.user_message, full_req.context)

	response = {
	"model_response": model_response
	}

	return response
