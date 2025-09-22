import jwt
import requests
import time

from sympy.codegen.fnodes import use_rename

from audit import audit_log
from Heuristic.HeuristicAnalyser import PromptInjectionClassifier
import os
from service_scripts.get_private_key import get_private_key
from service_scripts.yandex_cloud_embeddings import YandexCloudEmbeddings

FOLDER_ID = os.getenv('FOLDER_ID')
KEY_ID = os.getenv('KEY_ID')
SERVICE_ACCOUNT_ID = os.getenv('SERVICE_ACCOUNT_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
PRIVATE_KEY = get_private_key()

class YandexGPTBot:
    def __init__(self, rag_model, classifier, db):
        self.iam_token = None
        self.token_expires = 0
        self.KEY_ID = KEY_ID
        self.SERVICE_ACCOUNT_ID = SERVICE_ACCOUNT_ID
        self.PRIVATE_KEY = PRIVATE_KEY
        self.FOLDER_ID = FOLDER_ID
        self.embeddings = YandexCloudEmbeddings()
        self.rag_model = rag_model
        self.classifier = classifier
        self.db = db

        with open('system_prompt.txt', 'r') as f:
            self.system_template_true = f.read()

        with open('system_prompt_false.txt', 'r') as f:
            self.system_template_false = f.read()

        with open('system_epta_prompt.txt', 'r') as f:
            self.system_template_epta = f.read()

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

            audit_log("gpt_bot", "INFO", "IAM token generated successfully")
            return self.iam_token

        except Exception as e:
            audit_log("gpt_bot", "ERROR", f"Error generating IAM token: {str(e)}")
            raise

    def ask_gpt(self, question, user_id):
        """Запрос к Yandex GPT API"""
        try:
            iam_token = self.get_iam_token()

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {iam_token}',
                'x-folder-id': self.FOLDER_ID
            }

            rag_answer = self.rag_model.rag_request(question)

            valid_stat = self.classifier.analyze_text(question)
            audit_log("gpt_bot", "INFO", f"Сообщение пользователя: {question}. Риск = {valid_stat}")

            # ЗДЕСЬ НУЖНО ОПРЕДЕЛЯТЬ ПО РИСКУ ХУЕВЫЙ ЛИ ЗАПРОС И ЧТО С ЭТИМ ДЕЛАТЬ

            chat_history = self.db.get_conversation_history(user_id)
            user_name = self.db.get_user_name(user_id)

            if len(rag_answer) > 20:
                system_prompt = f'Ты — ассистент, который отвечает от лица персонажа (Гарри Поттера), описанного в предоставленной информации. Твоя цель — вести диалог уважительно, безопасно и этично. Вот контекст, найденный в системе по запросу пользователя: {rag_answer}. А вот имя пользователя, по которому ты можешь к нему обращаться, если нужно: {user_name}. Обращайся к пользователю именно так! Если он спросит как его зовут, скажи это имя! А также история вашего общения: {chat_history}. {self.system_template_true}'
            else:
                system_prompt = self.system_template_false

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
                audit_log("gpt_bot", "ERROR", f"Yandex GPT API error: {response.text}")
                raise Exception(f"Ошибка API: {response.status_code}")

            return response.json()['result']['alternatives'][0]['message']['text']

        except Exception as e:
            audit_log("gpt_bot", "ERROR", f"Error in ask_gpt: {str(e)}")
            raise
