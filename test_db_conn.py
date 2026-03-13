import streamlit as st
from supabase import create_client
import os

# Mock streamlit secrets loading if running as standalone script
# (Streamlit secrets are usually handled by `streamlit run`, but `st.secrets` works if .streamlit/secrets.toml exists and we use `streamlit run` OR we can manual load for this test script if we want to run with python directly. 
# Actually `st.secrets` requires `streamlit run`. 
# Let's just parse the toml file directly to be independent of streamlit for this quick test, 
# OR just run it with streamlit.)

# Simpler: Parse toml manually to test the file content + connection
import toml

try:
    secrets = toml.load(".streamlit/secrets.toml")
    url = secrets["SUPABASE_URL"]
    key = secrets["SUPABASE_KEY"]
    
    print(f"Found URL: {url[:10]}...")
    print(f"Found KEY: {key[:10]}...")
    
    client = create_client(url, key)
    res = client.table("fanout_analyses").select("count", count="exact").execute()
    print("Connection successful!")
    print(f"Current analysis count: {res.count}")
    
except Exception as e:
    print(f"Connection failed: {e}")
