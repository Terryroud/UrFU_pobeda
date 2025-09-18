import jwt
import requests
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

class YandexGPTBot:
    def __init__(self, logger, rag_model):
        self.iam_token = None
        self.token_expires = 0
        self.KEY_ID = KEY_ID
        self.SERVICE_ACCOUNT_ID = SERVICE_ACCOUNT_ID
        self.PRIVATE_KEY = PRIVATE_KEY
        self.FOLDER_ID = FOLDER_ID
        self.logger = logger
        self.embeddings = YandexCloudEmbeddings()
        self.rag_model = rag_model

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

            self.logger.info("IAM token generated successfully")
            return self.iam_token

        except Exception as e:
            self.logger.error(f"Error generating IAM token: {str(e)}")
            raise

    def validation_request(self, question):
        # Создаем классификатор
        classifier = PromptInjectionClassifier(question)

        # Показываем начальную статистику
        stats = classifier.get_vector_stats()

        # Анализируем текст
        result = classifier.analyze_text()
        return result

    def ask_gpt(self, question):
        """Запрос к Yandex GPT API"""
        try:
            iam_token = self.get_iam_token()

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {iam_token}',
                'x-folder-id': self.FOLDER_ID
            }

            rag_answer = self.rag_model.rag_request(question)

            # valid_stat = self.validation_request(question)
            # self.logger.info(f"Риск = {valid_stat['total_risk_score']}")

            # ЗДЕСЬ НУЖНО ОПРЕДЕЛЯТЬ ПО РИСКУ ХУЕВЫЙ ЛИ ЗАПРОС И ЧТО С ЭТИМ ДЕЛАТЬ

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
                self.logger.error(f"Yandex GPT API error: {response.text}")
                raise Exception(f"Ошибка API: {response.status_code}")

            return response.json()['result']['alternatives'][0]['message']['text']

        except Exception as e:
            self.logger.error(f"Error in ask_gpt: {str(e)}")
            raise