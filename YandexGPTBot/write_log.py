import requests
import os
from dotenv import load_dotenv

load_dotenv()

AUDIT_URL = os.getenv("AUDIT_URL", "http://audit:8004")

def audit_log(service: str, level: str, message: str):
    try:
        payload = {"service": service, "level": level, "message": message}
        requests.post(AUDIT_URL, json=payload, timeout=2)
    except requests.RequestException:
        # Fallback: if audit service is down, maybe log locally
        print("Failed to send audit log")
