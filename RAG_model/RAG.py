import os
from audit import audit_log
from dotenv import load_dotenv
from service_scripts.get_private_key import get_private_key
import boto3
from tempfile import NamedTemporaryFile
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from service_scripts.yandex_cloud_embeddings import YandexCloudEmbeddings
import requests

# Импорт и настройка переменных окружения
load_dotenv()

FOLDER_ID = os.getenv('FOLDER_ID')
KEY_ID = os.getenv('KEY_ID')
SERVICE_ACCOUNT_ID = os.getenv('SERVICE_ACCOUNT_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
S3_ACCESS_KEY = os.getenv('STATIC_ACCESS_KEY_ADMIN')
S3_SECRET_KEY = os.getenv('STATIC_PRIVATE_KEY_ADMIN')
S3_BUCKET = os.getenv('S3_BUCKET')
PRIVATE_KEY = get_private_key()

class RAG:
    def __init__(self, score_threshold=0.7, chunk_size=500, chunk_overlap=50, chunk_count=5):
        self.score_threshold = score_threshold
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunk_count = chunk_count


        self.s3 = boto3.client(
            's3',
            endpoint_url='https://storage.yandexcloud.net',
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY
        )
        self.embeddings = YandexCloudEmbeddings()
        # self.logger = logger

    def load_document_from_s3(self, bucket_name: str, path: str):
        with NamedTemporaryFile(delete=False, suffix=os.path.splitext(path)[1]) as tmp_file:
            self.s3.download_fileobj(bucket_name, path, tmp_file)
            temp_path = tmp_file.name

        try:
            if path.endswith(".pdf"):
                loader = PyPDFLoader(temp_path)
            elif path.endswith(".txt"):
                loader = TextLoader(temp_path, encoding="utf-8")
            else:
                raise ValueError(f"Unsupported file format: {path}")

            loaded = loader.load()
            return loaded

        finally:
            os.unlink(temp_path)


    def get_list_files_in_s3_folder(self, bucket_name: str, folder_prefix: str):
        files = []

        response = self.s3.list_objects_v2(
            Bucket=bucket_name,
            Prefix=folder_prefix
        )

        for obj in response.get('Contents', []):
            if not obj['Key'].endswith('/'):
                files.append(obj['Key'])

        return files

    def get_files_from_cloud(self):
        # files = self.get_list_files_in_s3_folder("rag-db", "pizzaman/")

        files = ['pizzaman/harry_mini.txt']
        documents = [self.load_document_from_s3(S3_BUCKET, file)[0] for file in files]

        valid_documents = [document for document in documents
                           if hasattr(document, 'page_content') and
                           isinstance(document.page_content, str) and
                           document.page_content.strip()]

        return valid_documents

    def splitting_into_chunks(self):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )

        chunks = text_splitter.split_documents(self.get_files_from_cloud())
        return chunks

    def create_faiss_index(self):
        vectorstore = FAISS.from_documents(self.splitting_into_chunks(), self.embeddings)
        vectorstore.save_local("./vectorstore_faiss")
        # self.logger.info("Faiss create successful")
        audit_log("rag", "INFO", "Faiss create successful")

    def rag_request(self, question):
        vectorstore = FAISS.load_local("./vectorstore_faiss", self.embeddings, allow_dangerous_deserialization=True)
        docs_with_scores = vectorstore.similarity_search_with_score(question, k=self.chunk_count)

        filtered_docs = []
        for doc, score in docs_with_scores:
            if score <= 1.0 + self.score_threshold:
                filtered_docs.append(doc)

        context_chunks = "\n\n".join([doc.page_content for doc in filtered_docs])
        # self.logger.info(f"RAG нашел {len(filtered_docs)} подходящих чанков.")
        audit_log("rag", "INFO", f"RAG нашел {len(filtered_docs)} подходящих чанков.")

        return context_chunks
