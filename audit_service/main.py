from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import os
from datetime import datetime
import json

app = FastAPI(title="Audit Service")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/audit.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('audit')


class LogRequest(BaseModel):
    service: str
    level: str
    message: str
    user_id: int = None
    timestamp: str = None


@app.post("/log")
async def log_message(request: LogRequest):
    """Прием логов от оркестратора"""
    try:
        timestamp = request.timestamp or datetime.now().isoformat()

        # Маппинг уровней логирования
        log_func = {
            "DEBUG": logger.debug,
            "INFO": logger.info,
            "WARNING": logger.warning,
            "ERROR": logger.error,
            "CRITICAL": logger.critical,
        }.get(request.level.upper(), logger.info)

        # Форматируем сообщение
        user_info = f" user_id={request.user_id}" if request.user_id else ""
        log_message = f"[{request.service}{user_info}] {request.message}"
        log_func(log_message)

        return {
            "status": "success",
            "message": "Log recorded",
            "timestamp": timestamp
        }
    except Exception as e:
        logger.error(f"Error recording log: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch-log")
async def batch_log(messages: list[LogRequest]):
    """Массовая запись логов"""
    try:
        results = []
        for request in messages:
            result = await log_message(request)
            results.append(result)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs")
async def get_logs(service: str = None, level: str = None, user_id: int = None, limit: int = 100):
    """Получение логов (для администрирования)"""
    try:
        log_file = '/app/logs/audit.log'
        if not os.path.exists(log_file):
            return {"logs": [], "count": 0}

        with open(log_file, 'r', encoding='utf-8') as f:
            logs = f.readlines()[-limit:]

        filtered_logs = []
        for log in logs:
            if service and service not in log:
                continue
            if level and level.upper() not in log:
                continue
            if user_id and str(user_id) not in log:
                continue
            filtered_logs.append(log.strip())

        return {
            "logs": filtered_logs[::-1],
            "count": len(filtered_logs)
        }
    except Exception as e:
        logger.error(f"Error reading logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "audit"}


@app.get("/stats")
async def get_stats():
    """Статистика логов"""
    try:
        log_file = '/app/logs/audit.log'
        if not os.path.exists(log_file):
            return {"total_logs": 0, "services": {}}

        with open(log_file, 'r', encoding='utf-8') as f:
            logs = f.readlines()

        stats = {
            "total_logs": len(logs),
            "services": {},
            "levels": {}
        }

        for log in logs:
            # Простой анализ логов
            for service in ["orchestrator", "telegram-bot", "rag", "ai", "security", "database"]:
                if service in log:
                    stats["services"][service] = stats["services"].get(service, 0) + 1

            for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                if level in log:
                    stats["levels"][level] = stats["levels"].get(level, 0) + 1

        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    os.makedirs('/app/logs', exist_ok=True)
    logger.info("Audit Service starting...")
    uvicorn.run(app, host="0.0.0.0", port=8005)