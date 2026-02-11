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

def classify_queries(client, queries):
    """
    Classifies a list of queries into search intents: Informational, Commercial, Transactional, Navigational.
    Returns a list of dictionaries: [{'query': q, 'intent': i, 'icon': icon}, ...]
    """
    if not queries:
        return []

    try:
        prompt = f"""
        Classify the following search queries into one of these 4 intents:
        - Informational (Looking for information/answers)
        - Commercial (Investigating products/services)
        - Transactional (Ready to buy/act)
        - Navigational (Looking for a specific website)

        Queries:
        {json.dumps(queries)}

        Return a JSON array of objects with keys: "query", "intent", "icon".
        For "icon", use exactly one of these emojis: 🔵 (Info), 🟡 (Comm), 🟢 (Trans), 🟣 (Nav).
        Example: [{{"query": "best shoes", "intent": "Commercial", "icon": "🟡"}}]
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        return json.loads(response.text)
    except Exception as e:
        # Fallback if classification fails
        return [{"query": q, "intent": "Unknown", "icon": "⚪"} for q in queries]

def check_brand_visibility(client, query, brands, target_country="Denmark", persona_instruction=None):
    """
    Executes a search query using Gemini (with Grounding) and checks if any of the target brands
    are mentioned in the response.
    Returns: {'mentioned': bool, 'brands_found': [], 'snippet': str, 'response_text': str}
    """
    try:
        # Construct prompt for the deep check
        base_prompt = f"Context: Target market is {target_country}.\nUser Query: {query}\n\nPlease provide a helpful, comprehensive answer based on Google Search results."
        
        if persona_instruction:
            prompt_text = f"{persona_instruction}\n\n{base_prompt}"
        else:
            prompt_text = base_prompt
            
        # Configure tool with Google Search
        search_tool = types.Tool(google_search=types.GoogleSearch())
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_text,
            config=types.GenerateContentConfig(
                tools=[search_tool]
            )
        )
        
        full_text = response.text if response.text else ""
        text_lower = full_text.lower()
        
        found_brands = []
        snippet = ""
        
        for brand in brands:
            if brand.lower() in text_lower:
                found_brands.append(brand)
                
                # Capture snippet for the first found brand
                if not snippet:
                    idx = text_lower.find(brand.lower())
                    start = max(0, idx - 60)
                    end = min(len(full_text), idx + len(brand) + 60)
                    snippet = "..." + full_text[start:end].replace('\n', ' ') + "..."
        
        return {
            "query": query,
            "mentioned": len(found_brands) > 0,
            "brands_found": found_brands,
            "snippet": snippet,
            "full_response": full_text[:5000] + "..." if len(full_text) > 5000 else full_text
        }
        
    except Exception as e:
        return {
            "query": query,
            "mentioned": False,
            "brands_found": [],
            "snippet": f"Error during check: {str(e)}",
            "full_response": ""
        }

def generate_fan_out_queries(client, prompt, target_country="Denmark", persona_instruction=None):
    """
    Generates fan-out queries using Gemini 2.0 Flash with Google Search Grounding.
    Extracts raw search queries from the metadata.
    """
    try:
        # Prompt designed to trigger search naturally ("Naked Prompt" style)
        # FEATURE 1: COUNTRY PERSONA (Injected here)
        base_prompt = f"Context: Target market is {target_country}.\nUser Query: {prompt}\n\nPlease perform a comprehensive search to provide a detailed answer. Cover all aspects including intent, competitors, and background."
        
        if persona_instruction:
            prompt_text = f"{persona_instruction}\n\n{base_prompt}"
        else:
            prompt_text = base_prompt
        
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
        
        # Enforce distinct result types
        classified_queries = classify_queries(client, queries)
                
        return {
            "original_prompt": prompt,
            "raw_queries": queries,
            "classified_queries": classified_queries
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
                "Raw Search Queries": f"ERROR: {data['error']}",
                "Classified Data": "[]"
            }
        else:
            queries_list = data.get("raw_queries", [])
            classified = data.get("classified_queries", [])
            
            formatted_queries = "\n".join(queries_list) if queries_list else "No search queries generated."
            
            row = {
                "Primary Prompt": prompt,
                "Raw Search Queries": formatted_queries,
                "Classified Data": json.dumps(classified) # Store as string for CSV safety
            }
        
        results.append(row)
        
    return pd.DataFrame(results)
