from fastapi import FastAPI, HTTPException
from HeuristicAnalyser import PromptInjectionClassifier
import os

app = FastAPI(title="Security Service")

classifier = PromptInjectionClassifier(
    vectors_file="vectors.json",
    threshold=0.7,
    risk_threshold=1.5,
    insertion_cost=1,
    deletion_cost=1,
    substitution_cost=1
)


@app.post("/check-safety")
async def check_safety(request: dict):
    """Проверка безопасности текста"""
    try:
        text = request.get('text', '')
        is_invalid, valid_stat = classifier.analyze_text(text)

        return {
            "is_invalid": is_invalid,
            "valid_stat": valid_stat,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "security"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)