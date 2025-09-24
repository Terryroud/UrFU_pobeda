import requests

VALID_URL = "http://localhost:8001/valid/"
RAG_URL = "http://localhost:8002/rag/"
AGENT_URL = "http://localhost:8003/agent/"
AUDIT_URL = "http://localhost:8004/audit/"
DB_URL = "http://localhost:8005"

# log request
def audit_log(service: str, level: str, message: str):
    try:
        payload = {"service": service, "level": level, "message": message}
        requests.post(AUDIT_URL, json=payload, timeout=2)
    except requests.RequestException:
        # Fallback: if audit service is down, maybe log locally
        print("Failed to send audit log")

# validation request
def analyze_text(text: str):
    try:
        payload = {
        "text": text
        }

        resp = requests.post(VALID_URL, json=payload, timeout=5)
        resp.raise_for_status()
        return resp.json()['is_invalid'], resp.json()['valid_stat']
    except requests.RequestException:
        audit_log("orchestrator", "ERROR", "Error sending validation request")

# context request
def rag_request(question: str):
    try:
        payload = {"question": question}
        resp = requests.post(RAG_URL, json=payload, timeout=5)
        resp.raise_for_status()
        return resp.json()['context']
    except requests.RequestException:
        audit_log("orchestrator", "ERROR", "Error sending rag request")

# llm request
def agent_request(
    user_message: str, 
    chat_history: str,
    user_name: str,
    rag_answer: str,
    is_invalid: bool,
    valid_stat: float):
    try:
        payload = {
        "user_message": user_message,
        "chat_history": chat_history,
        "user_name": user_name,
        "rag_answer": rag_answer,
        "is_invalid": is_invalid,
        "valid_stat": valid_stat
        }

        resp = requests.post(AGENT_URL, json=payload, timeout=5)
        resp.raise_for_status()
        return resp.json()['model_response']
    except requests.RequestException:
        audit_log("orchestrator", "ERROR", "Error sending request to model")


# db requests

# add user
def add_user(user_id: int,
        username: str,
        first_name: str,
        last_name: str):
    
    try:
        payload = {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name
        }

        resp = requests.post(
            f"{DB_URL}/database/add_user",
            json=payload, timeout=5
        )
        resp.raise_for_status()
        return resp.json().get("status") == "ok"
    except requests.RequestException:
        audit_log("orchestrator", "ERROR", f"Error adding new user with user_id={user_id}")
        return False


# get user name
def get_user_name(user_id: int):
    try:
        resp = requests.get(
            f"{DB_URL}/database/get_user_name/{user_id}",
            timeout=5
        )
        resp.raise_for_status()
        return resp.json().get("user_name")
    except requests.RequestException:
        audit_log("orchestrator", "ERROR", f"Error getting username for user_id={user_id}")
        return None


# update user name
def update_user_name(user_id: int, new_username: str):
    try:
        payload = {
            "user_id": user_id,
            "username": new_username
        }
        resp = requests.patch(
            f"{DB_URL}/database/update_user_name",
            json=payload,
            timeout=5
        )
        resp.raise_for_status()
        return resp.json().get("status") == "ok"
    except requests.RequestException:
        audit_log("orchestrator", "ERROR", f"Error updating username for user_id={user_id}")
        return False


# delete user
def delete_user(user_id: int):
    try:
        resp = requests.delete(
            f"{DB_URL}/database/delete_user/{user_id}",
            timeout=5
        )
        resp.raise_for_status()
        return resp.json().get("status") == "ok"
    except requests.RequestException:
        audit_log("orchestrator", "ERROR", f"Error deleting user_id={user_id}")
        return False


# get chat history
def get_history(user_id: int, limit: int = 50):
    try:
        resp = requests.get(
            f"{DB_URL}/database/get_history/{user_id}", 
            params={"limit": limit}, timeout=5
        )

        resp.raise_for_status()
        return resp.json()['history']
    except requests.RequestException:
        audit_log("orchestrator", "ERROR", "Error sending getting chat history")

def add_message(user_id: int, message_text: str, bot_response: str):
    try:
        payload = {
        "user_id": user_id,
        "message_text": message_text,
        "bot_response": bot_response
        }
        resp = requests.post(
            f"{DB_URL}/database/add_message/",
            json=payload,
            timeout=5
        )
        resp.raise_for_status()
        return resp.json().get("status") == "ok"
    except requests.RequestException:   
        audit_log("orchestrator", "ERROR", f"Error adding message for user_id={user_id}")
        return False
