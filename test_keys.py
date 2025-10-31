import os
from dotenv import load_dotenv
import google.generativeai as genai
from anthropic import Anthropic

load_dotenv()

# Test Gemini
try:
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel('models/gemini-flash-lite-latest')
    response = model.generate_content("Say 'Gemini works'")
    print(f"[SUCCESS] Gemini: {response.text}")
except Exception as e:
    print(f"[ERROR] Gemini: {e}")

# Test Anthropic
try:
    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{"role": "user", "content": "Say 'Claude works'"}]
    )
    print(f"[SUCCESS] Claude: {message.content[0].text}")
except Exception as e:
    print(f"[ERROR] Claude: {e}")