from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel
import requests
from HeuristicAnalyser import PromptInjectionClassifier

classifier = PromptInjectionClassifier(
    vectors_file="vectors.json",
    threshold=0.7,
    risk_threshold=1.5,
    insertion_cost=1,
    deletion_cost=1,
    substitution_cost=1
)

app = FastAPI(title="Validator", docs_url=None, redoc_url=None, openapi_url=None)

class ValidRequest(BaseModel):
	text: str


@app.post("/valid/")
async def analyze_text(user_message: ValidRequest):
	is_invalid, valid_stat = classifier.analyze_text(user_message.text)

	response = {
	"is_invalid": is_invalid,
	"valid_stat": valid_stat
	}

	return response

@app.get("/health")
def health_check():
    return {"status": "ok"}
