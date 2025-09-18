import logging
from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel


# ---------- Logging Setup ----------
logger = logging.getLogger('my_logger')
logger.setLevel(logging.DEBUG)


formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

file_handler = logging.FileHandler('app.log', encoding='utf=8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

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
