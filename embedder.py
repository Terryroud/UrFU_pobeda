from yandex_cloud_ml_sdk import YCloudML
import numpy as np
from scipy.spatial.distance import cdist
import os
from dotenv import load_dotenv
from pathlib import Path

# Импорт и настройка переменных окружения
load_dotenv()

FOLDER_ID = os.getenv('FOLDER_ID')
API_KEY = 'AQVNwZuEPQuhTU6inrwSWJzmfOydcsqVct1FJplx'

sdk = YCloudML(folder_id=FOLDER_ID, auth=API_KEY)

# выбрать модель: query (короткие промпты) или doc (длинные тексты)
query_model = sdk.models.text_embeddings("query")  # эквивалент emb://.../text-search-query/latest
doc_model = sdk.models.text_embeddings("doc")      # emb://.../text-search-doc/latest

def get_embedding_textsdk(text: str, text_type: str = "query") -> np.ndarray:
    model = query_model if text_type == "query" else doc_model
    emb = model.run(text)  # возвращает list[float]
    return np.array(emb, dtype=np.float32)


#print(get_embedding_textsdk("Сырный суп"))
