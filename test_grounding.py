import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

def test_tool_config():
    print(f"SDK Version: {genai.__version__}")
    
    # Attempt 1: Dictionary format
    print("\nAttempt 1: Dictionary format tools={'google_search': {}}")
    try:
        # Note: 'tools' argument expects a list or a single tool object. 
        # For dictionary config, it is often passed directly as a tool list item.
        model = genai.GenerativeModel('gemini-2.5-flash', tools=[{'google_search': {}}])
        response = model.generate_content("What represents the user request in testing?", request_options={"timeout": 600})
        print("✅ Success!")
        print(response.text)
    except Exception as e:
        print(f"❌ Failed: {e}")

    # Attempt 3: GoogleSearchRetrieval (Old way, maybe just verify)
    print("\nAttempt 3: protos.GoogleSearchRetrieval")
    try:
        t = genai.protos.Tool(google_search_retrieval=genai.protos.GoogleSearchRetrieval(dynamic_retrieval_config=genai.protos.DynamicRetrievalConfig(mode=genai.protos.DynamicRetrievalConfig.Mode.MODE_DYNAMIC)))
        model = genai.GenerativeModel('gemini-2.5-flash', tools=[t])
        response = model.generate_content("What is the weather in Copenhagen?")
        print("✅ Success!")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    test_tool_config()
