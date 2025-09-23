import requests

AUDIT_URL = "http://localhost:8004/audit/"

def audit_log(service: str, level: str, message: str):
    try:
        payload = {"service": service, "level": level, "message": message}
        requests.post(AUDIT_URL, json=payload, timeout=2)
    except requests.RequestException:
        # Fallback: if audit service is down, maybe log locally
        print("Failed to send audit log")
