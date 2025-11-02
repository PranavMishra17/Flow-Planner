"""Check available Claude models with image capability"""
from anthropic import Anthropic
from dotenv import load_dotenv
import os

load_dotenv()

client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Get models
try:
    response = client.models.list()
    print("\n[INFO] Available Claude models:")
    print("=" * 80)
    for model in response.data:
        print(f"  - {model.id}")
        if hasattr(model, 'display_name'):
            print(f"    Display Name: {model.display_name}")
        if hasattr(model, 'vision'):
            print(f"    Vision: {model.vision}")
    print("=" * 80)
except Exception as e:
    print(f"[ERROR] {e}")
    print("\n[INFO] The /models endpoint may not be available.")
    print("[INFO] Known models with vision capability:")
    print("  - claude-3-5-sonnet-20241022 (highest quality)")
    print("  - claude-3-5-haiku-20241022 (faster, cheaper)")
    print("  - claude-haiku-4-5-20251001 (latest haiku)")
    print("  - claude-3-opus-20240229 (previous generation)")
    print("  - claude-3-sonnet-20240229 (previous generation)")
    print("  - claude-3-haiku-20240307 (previous generation)")
