from RAG import RAG
from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel

rag_model = RAG(score_threshold=0.5, chunk_size=500, chunk_overlap=150, chunk_count=5)
rag_model.create_faiss_index()

app = FastAPI(title="RAG", docs_url=None, redoc_url=None, openapi_url=None)

class Question(BaseModel):
    question: str

@app.post("/rag/")
async def context_request(question: Question, request: Request):
	rag_answer = rag_model.rag_request(question.question)

	response = {
	"context": rag_answer
	}

	return response

@app.get("/health")
def health_check():
    return {"status": "ok"}
