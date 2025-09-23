from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

def get_private_key():
    key_path = Path(os.getenv('PRIVATE_KEY'))

    # if not key_path.is_absolute():
    #     key_path = Path(__file__).parent / key_path

    if not key_path.exists():
        raise FileNotFoundError(f"Файл с приватным ключом не найден: {key_path}")

    try:
        with open(key_path, 'rb') as key_file:
            key_file.readline()
            return key_file.read()

    except Exception as e:
        raise Exception(f"Ошибка загрузки приватного ключа: {e}")