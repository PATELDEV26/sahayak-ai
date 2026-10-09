import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env in the same directory as this file or current working directory is loaded with override=True
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

from groq import Groq

api_key = os.environ.get('GROQ_API_KEY') or os.environ.get('GROK_API_KEY')
if not api_key:
    raise ValueError("GROQ_API_KEY is not set. Please set it in .env or environment.")
client = Groq(api_key=api_key)

try:
    models = client.models.list()
    for m in models.data:
        print(m.id)
except Exception as e:
    print("Error:", e)
