from langchain.embeddings.base import Embeddings
from typing import List
from service_scripts.embedder import get_embedding_textsdk

class YandexCloudEmbeddings(Embeddings):
    def __init__(self, text_type: str = "doc"):
        self.text_type = text_type

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Создает эмбеддинги для документов"""
        embeddings = []
        for text in texts:
            emb = get_embedding_textsdk(text, text_type="doc")
            embeddings.append(emb.tolist())
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Создает эмбеддинг для запроса"""
        emb = get_embedding_textsdk(text, text_type="query")
        return emb.tolist()