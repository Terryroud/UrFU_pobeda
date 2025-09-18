from fastapi import FastAPI
from pydantic import BaseModel
import logging
from datetime import datetime
import os

app = FastAPI()

# Setup logging to file
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/central.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("central_logger")

class LogEntry(BaseModel):
    level: str
    message: str
    service: str

@app.post("/log")
async def log_entry(entry: LogEntry):
    # Log to file
    log_level = getattr(logging, entry.level.upper(), logging.INFO)
    logger.log(log_level, f"[{entry.service}] {entry.message}")
    return {"status": "logged"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
