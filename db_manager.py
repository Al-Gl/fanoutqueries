import os
import streamlit as st
from supabase import create_client, Client
import json
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
def init_supabase():
    """Initializes and returns the Supabase Client."""
    # Try secrets first, then env vars
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        return None
        
    return create_client(url, key)

# --- SAVE FUNCTIONS ---
def save_analysis(inputs, results_df):
    """
    Saves a complete analysis run to Supabase.
    Args:
        inputs (dict): The configuration used (country, brand, etc).
        results_df (pd.DataFrame): The resulting dataframe from the run.
    """
    supabase = init_supabase()
    if not supabase:
        return False, "Supabase credentials not found."

    try:
        # 1. Create Analysis Record (The "Header")
        analysis_data = {
            "target_country": inputs.get('target_country'),
            "primary_brand": inputs.get('primary_brand'),
            # specific handling for list inputs just in case
            "competitors": inputs.get('competitors', '').split(',') if isinstance(inputs.get('competitors'), str) else inputs.get('competitors'),
            "original_prompts": [p for p in inputs.get('prompt', '').split('\n') if p.strip()],
            "total_queries": len(results_df) if results_df is not None else 0,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Clean up competitors list
        if isinstance(analysis_data['competitors'], list):
            analysis_data['competitors'] = [c.strip() for c in analysis_data['competitors'] if c.strip()]

        response = supabase.table("fanout_analyses").insert(analysis_data).execute()
        
        if not response.data:
            return False, "Failed to create analysis record."
            
        analysis_id = response.data[0]['id']
        
        # 2. Create Result Records (The "Rows")
        results_to_insert = []
        
        for _, row in results_df.iterrows():
            # Parse JSON strings coming from DataFrame
            try:
                classified = json.loads(row.get("Classified Data", "[]"))
                deep_data = json.loads(row.get("Deep Data", "[]"))
            except:
                classified = []
                deep_data = []
            
            # We need to flatten this. 
            # The current DF structure is 1 Row per Prompt -> Many Deep Results.
            # But we want to store granularity at the "Fan Out Query" level or even "Prompt" level?
            # Let's store at the Query level for better querying later, OR store the big JSONs.
            # Plan: Store 1 row per Fan-Out Query generated.
            
            # Since the DF row corresponds to a Primary Prompt, let's iterate its deep results
            if not deep_data and not classified:
                # Just store the prompt if everything failed
                results_to_insert.append({
                    "analysis_id": analysis_id,
                    "primary_prompt": row.get("Primary Prompt"),
                    "fanout_query": None,
                    "raw_data_dump": json.dumps(row.to_dict()) # Fallback
                })
            
            # Strategy: We will create one record per "Deep Analysis" result (Fan-out Query)
            # This allows granular "how many times did brand X appear" queries.
            
            for item in deep_data:
                # item structure: {'query': '...', 'mentioned': bool, 'brands_found': [...], ...}
                
                # Match classification data if possible (mapping back by query string is brittle but best effort)
                intent_data = next((c for c in classified if c.get('query') == item.get('query')), {})
                
                record = {
                    "analysis_id": analysis_id,
                    "primary_prompt": row.get("Primary Prompt"),
                    "fanout_query": item.get('query'),
                    "intents": intent_data.get('intents', []),
                    "brands_found": item.get('brands_found', []),
                    "snippet": item.get('snippet'),
                    "full_response": item.get('full_response'),
                    "is_primary_found": inputs.get('primary_brand', '').lower() in [b.lower() for b in item.get('brands_found', [])] if inputs.get('primary_brand') else False,
                    "is_competitor_found": any(c.lower() in [b.lower() for b in item.get('brands_found', [])] for c in analysis_data['competitors'])
                }
                results_to_insert.append(record)
                
            # If we had no deep data (e.g. just classified but not deep analyzed?), Handle that edge case
            if classified and not deep_data:
                 for item in classified:
                    record = {
                        "analysis_id": analysis_id,
                        "primary_prompt": row.get("Primary Prompt"),
                        "fanout_query": item.get('query'),
                        "intents": item.get('intents', []),
                        "brands_found": [],
                        "snippet": None
                    }
                    results_to_insert.append(record)

        if results_to_insert:
            # Batch insert
            supabase.table("fanout_results").insert(results_to_insert).execute()
            
        return True, analysis_id

    except Exception as e:
        return False, str(e)

# --- FETCH FUNCTIONS ---
def get_history():
    """Fetches list of past analyses."""
    supabase = init_supabase()
    if not supabase: return []
    
    try:
        response = supabase.table("fanout_analyses").select("*").order("created_at", desc=True).limit(50).execute()
        return response.data
    except Exception:
        return []

def load_analysis(analysis_id):
    """
    Loads a specific analysis and reconstructs the DataFrame format expected by the app.
    """
    supabase = init_supabase()
    if not supabase: return None, None
    
    try:
        # 1. Get Metadata
        meta_response = supabase.table("fanout_analyses").select("*").eq("id", analysis_id).execute()
        if not meta_response.data: return None, None
        meta = meta_response.data[0]
        
        # 2. Get Results
        results_response = supabase.table("fanout_results").select("*").eq("analysis_id", analysis_id).execute()
        results_data = results_response.data
        
        # 3. Reconstruct DataFrame
        # The app expects: "Primary Prompt", "Raw Search Queries", "Classified Data" (json), "Deep Data" (json)
        
        # Group by Primary Prompt
        grouped = {}
        for r in results_data:
            pp = r.get('primary_prompt')
            if pp not in grouped:
                grouped[pp] = {'classified': [], 'deep': []}
            
            # Reconstruct Item Objects
            q_obj = {
                "query": r.get('fanout_query'),
                "intents": r.get('intents'),
                # Icons are static mapping in logic, maybe safe to omit or re-infer? 
                # For now let's just put placeholders or rely on app to handle missing icons
            }
            
            d_obj = {
                "query": r.get('fanout_query'),
                "mentioned": bool(r.get('brands_found')),
                "brands_found": r.get('brands_found'),
                "snippet": r.get('snippet'),
                "full_response": r.get('full_response')
            }
            
            grouped[pp]['classified'].append(q_obj)
            grouped[pp]['deep'].append(d_obj)
            
        rows = []
        for pp, data in grouped.items():
            rows.append({
                "Primary Prompt": pp,
                "Raw Search Queries": "\n".join([x['query'] for x in data['classified'] if x['query']]),
                "Classified Data": json.dumps(data['classified']),
                "Deep Data": json.dumps(data['deep'])
            })
            
        return meta, pd.DataFrame(rows)
        
    except Exception as e:
        st.error(f"Error loading analysis: {e}")
        return None, None
