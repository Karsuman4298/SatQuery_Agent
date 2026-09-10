import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()  

client = OpenAI(
    base_url=os.getenv("OPEN_ROUTER_BASE_URL", "https://openrouter.ai"),
    api_key=os.getenv("OPEN_ROUTER_API_KEY"), # Make sure this matches your .env file exactly!
)

print("OpenRouter client initialized successfully.")

try:
    response = client.chat.completions.create(
        model=os.environ.get("VISION_LANGUAGE_MODEL", "qwen/qwen-2.5-vl-7b-instruct:free"),
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, can you help me with a test?"}
        ],
        max_tokens=50,
        temperature=0.1,
    )
    print("Test request successful. Response:")
    print(response)
except Exception as e:
    print(f"Error during test request: {e}")