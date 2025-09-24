from fastapi import FastAPI, HTTPException

app = FastAPI(title="RAG Service")

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    global rag_model
    try:
        from RAG import RAG
        rag_model = RAG(score_threshold=0.5, chunk_size=500, chunk_overlap=150, chunk_count=5)
        rag_model.create_faiss_index()
    except Exception as e:
        raise


@app.get("/query")
async def query_rag(question: str):
    """Обработка запроса к RAG модели"""
    print(question)
    try:
        if not rag_model:
            raise HTTPException(status_code=503, detail="RAG model not initialized")

        if not question or not question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")

        result, chunks_count = rag_model.rag_request(question)

        return {
            "answer": result,
            "status": "success",
            "chunks_count": chunks_count
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)