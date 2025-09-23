from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

key_path = Path(os.getenv("PRIVATE_KEY", ""))
if not key_path.exists():
    raise FileNotFoundError(f"Key file not found at {key_path}")

key_content = key_path.read_text().strip()
print("Key preview:", key_content[:50])  # just to confirm headers

try:
    with open(key_path, 'rb') as key_file:
        key_file.readline()
        key_file.read()
