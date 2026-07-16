from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path(__file__).resolve().parent.parent / ".env"

print(env_path)

load_dotenv(env_path)

print("Exists:", bool(os.getenv("GOOGLE_API_KEY")))
print("Starts:", os.getenv("GOOGLE_API_KEY")[:6])
from google import genai

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

print("Testing Gemini...")

for model in client.models.list():
    print(model.name)