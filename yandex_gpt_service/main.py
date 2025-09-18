from fastapi import FastAPI
from pydantic import BaseModel
import requests
import jwt
import time
from Heuristic.HeuristicAnalyser import PromptInjectionClassifier
import os
from service_scripts.get_private_key import get_private_key
from service_scripts.yandex_cloud_embeddings import YandexCloudEmbeddings

FOLDER_ID = os.getenv('FOLDER_ID')
KEY_ID = os.getenv('KEY_ID')
SERVICE_ACCOUNT_ID = os.getenv('SERVICE_ACCOUNT_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
PRIVATE_KEY = get_private_key()

app = FastAPI()

def send_log(level, message, service="yandex_gpt_service"):
    try:
        requests.post("http://localhost:8001/log", json={"level": level, "message": message, "service": service}, timeout=5)
    except:
        pass

class YandexGPTBot:
    def __init__(self):
        self.iam_token = None
        self.token_expires = 0
        self.KEY_ID = KEY_ID
        self.SERVICE_ACCOUNT_ID = SERVICE_ACCOUNT_ID
        self.PRIVATE_KEY = PRIVATE_KEY
        self.FOLDER_ID = FOLDER_ID
        self.embeddings = YandexCloudEmbeddings()

    def get_iam_token(self):
        """Получение IAM-токена (с кэшированием на 1 час)"""
        if self.iam_token and time.time() < self.token_expires:
            return self.iam_token

        try:
            now = int(time.time())
            payload = {
                'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
                'iss': self.SERVICE_ACCOUNT_ID,
                'iat': now,
                'exp': now + 360
            }

            encoded_token = jwt.encode(
                payload,
                self.PRIVATE_KEY,
                algorithm='PS256',
                headers={'kid': self.KEY_ID}
            )

            response = requests.post(
                'https://iam.api.cloud.yandex.net/iam/v1/tokens',
                json={'jwt': encoded_token},
                timeout=10
            )

            if response.status_code != 200:
                raise Exception(f"Ошибка генерации токена: {response.text}")

            token_data = response.json()
            self.iam_token = token_data['iamToken']
            self.token_expires = now + 3500  # На 100 секунд меньше срока действия

            send_log("INFO", "IAM token generated successfully")
            return self.iam_token

        except Exception as e:
            send_log("ERROR", f"Error generating IAM token: {str(e)}")
            raise

    def validation_request(self, question):
        # Создаем классификатор
        classifier = PromptInjectionClassifier(question)

        # Показываем начальную статистику
        stats = classifier.get_vector_stats()
        send_log("INFO", f"Request: {question}. Initial load: {stats['total_vectors']} vectors")

        # Анализируем текст
        result = classifier.analyze_text()
        send_log("INFO", f"Request: {question}. Risk = {result['total_risk_score']}")

        # ЗДЕСЬ НУЖНО ОПРЕДЕЛЯТЬ ПО РИСКУ ХУЕВЫЙ ЛИ ЗАПРОС И ЧТО С ЭТИМ ДЕЛАТЬ./vectorstore_faiss

    def ask_gpt(self, question):
        """Запрос к Yandex GPT API"""
        try:
            iam_token = self.get_iam_token()

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {iam_token}',
                'x-folder-id': self.FOLDER_ID
            }

            # Call RAG service
            rag_response = requests.post("http://localhost:8002/query", json={"question": question}, timeout=30)
            if rag_response.status_code == 200:
                rag_answer = rag_response.json().get("context", "")
            else:
                rag_answer = ""
                send_log("ERROR", f"RAG service error: {rag_response.text}")

            if len(rag_answer) > 20:
                system_prompt = f'Вот информация, которую система нашла во внутренней БД по запросу пользователя: {rag_answer}. Используй эту информацию для ответа на запрос.'
            else:
                system_prompt = 'Система не смогла найти информацию по запросу пользователя. Придумай ответ сам, либо напиши, что ответ не найден.'

            data = {
                "modelUri": f"gpt://{self.FOLDER_ID}/yandexgpt-lite",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.6,
                    "maxTokens": 2000
                },
                "messages": [
                    {
                        "role": "system",
                        "text": system_prompt
                    },
                    {
                        "role": "user",
                        "text": question
                    }
                ]
            }

            response = requests.post(
                'https://llm.api.cloud.yandex.net/foundationModels/v1/completion',
                headers=headers,
                json=data,
                timeout=30
            )

            if response.status_code != 200:
                send_log("ERROR", f"Yandex GPT API error: {response.text}")
                raise Exception(f"Ошибка API: {response.status_code}")

            return response.json()['result']['alternatives'][0]['message']['text']

        except Exception as e:
            send_log("ERROR", f"Error in ask_gpt: {str(e)}")
            raise

bot_instance = YandexGPTBot()

class AskGPTRequest(BaseModel):
    question: str

@app.post("/ask_gpt")
async def ask_gpt(request: AskGPTRequest):
    try:
        response = bot_instance.ask_gpt(request.question)
        return {"response": response}
    except Exception as e:
        send_log("ERROR", f"Error in /ask_gpt: {str(e)}")
        return {"error": str(e)}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
