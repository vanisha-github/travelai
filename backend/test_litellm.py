import os
from dotenv import load_dotenv
import litellm
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

response = litellm.completion(
    model="gemini/gemini-3.1-flash-lite",
    api_key=os.getenv("GOOGLE_API_KEY"),
    messages=[
        {
            "role": "user",
            "content": "Say hello in one sentence."
        }
    ]
)

print(response.choices[0].message.content)