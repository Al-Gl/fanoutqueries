import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

def get_client(api_key=None):
    """Initializes and returns the GenAI Client."""
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError("Gemini API Key not found. Please set GEMINI_API_KEY in .env or provide it in the UI.")
    
    return genai.Client(api_key=api_key.strip())

def generate_fan_out_queries(client, prompt, target_country="Denmark"):
    """
    Generates fan-out queries using Gemini 2.0 Flash with Google Search Grounding.
    Extracts raw search queries from the metadata.
    """
    try:
        # Prompt designed to trigger search naturally ("Naked Prompt" style)
        prompt_text = f"Context: Target market is {target_country}.\nUser Query: {prompt}\n\nPlease perform a comprehensive search to provide a detailed answer. Cover all aspects including intent, competitors, and background."
        
        # Configure tool
        search_tool = types.Tool(google_search=types.GoogleSearch())
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_text,
            config=types.GenerateContentConfig(
                tools=[search_tool]
            )
        )
        
        queries = []
        
        # Extract grounding metadata safely
        if response.candidates and response.candidates[0].grounding_metadata:
             metadata = response.candidates[0].grounding_metadata
             if metadata.web_search_queries:
                 queries = metadata.web_search_queries
                
        return {
            "original_prompt": prompt,
            "raw_queries": queries
        }
        
    except Exception as e:
        return {"error": str(e), "original_prompt": prompt}

def process_prompts(client, prompts_list, target_country="Denmark"):
    """
    Processes a list of prompts.
    """
    results = []
    
    for prompt in prompts_list:
        if not prompt or pd.isna(prompt):
            continue
            
        data = generate_fan_out_queries(client, prompt, target_country=target_country)
        
        if "error" in data:
            row = {
                "Primary Prompt": prompt,
                "Error": data["error"]
            }
        else:
            queries_list = data.get("raw_queries", [])
            formatted_queries = "\n".join(queries_list) if queries_list else "No search queries generated."
            
            row = {
                "Primary Prompt": prompt,
                "Raw Search Queries": formatted_queries
            }
        
        results.append(row)
        
    return pd.DataFrame(results)
