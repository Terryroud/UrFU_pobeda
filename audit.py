import logging


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


# class AuditLog(BaseModel):
# 	service: str
# 	level: str
# 	message: str

def audit_log(service: str, level: str, message: str):
    # client_host = request.client.host

    # Map string level to logging function
    log_func = {
        "DEBUG": logger.debug,
        "INFO": logger.info,
        "WARNING": logger.warning,
        "ERROR": logger.error,
        "CRITICAL": logger.critical,
    }.get(level, logger.info)

    log_func(f"[{service}] {message}")
    return {"status": "ok"}
