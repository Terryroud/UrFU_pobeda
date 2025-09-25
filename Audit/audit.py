import logging
from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel


# ---------- Logging Setup ----------
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf=8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('audit')
logging.getLogger().setLevel(logging.INFO)

# ---------- FastAPI App ----------
app = FastAPI(title="Audit Service", docs_url=None, redoc_url=None, openapi_url=None)


class AuditLog(BaseModel):
    service: str
    level: str
    message: str

@app.post("/audit/")
async def audit_log(entry: AuditLog, request: Request):
    client_host = request.client.host

    # Map string level to logging function
    level = entry.level.upper()
    log_func = {
        "DEBUG": logger.debug,
        "INFO": logger.info,
        "WARNING": logger.warning,
        "ERROR": logger.error,
        "CRITICAL": logger.critical,
    }.get(level, logger.info)

    log_func(f"[{entry.service}] {entry.message} (from {client_host})")
    return {"status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
