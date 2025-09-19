import logging


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
