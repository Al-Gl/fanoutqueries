import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ GOOGLE_API_KEY not found in .env file.")
else:
    print(f"✅ Found API Key: {api_key[:5]}...{api_key[-5:]}")
    try:
        genai.configure(api_key=api_key)
        print("\nListing available models...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"\n❌ Error listing models: {e}")
