import streamlit as st
import pandas as pd
import fan_out_logic
import os
import io
from google import genai

def initialize_client():
    """
    Retrieves the API key from Streamlit Secrets (Cloud) 
    or local secrets.toml.
    """
    # 1. Try to get the key from Streamlit's internal secrets
    api_key = st.secrets.get("GEMINI_API_KEY")
    
    # 2. Fallback: Check standard environment variables
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        st.error("🔑 **API Key Not Found!**")
        st.info("Local: Add it to `.streamlit/secrets.toml` \n\n Cloud: Add it to App Settings > Secrets.")
        st.stop()
        
    # Strict Validation: Strip whitespace
    api_key = api_key.strip()
    
    # Validation: Ensure it's not empty
    if not api_key:
        st.error("❌ **API Key is empty!**")
        st.stop()
        
    return genai.Client(api_key=api_key)


st.set_page_config(page_title="Fan-Out Query Tool", page_icon="🕸️", layout="wide")

st.title("🕸️ AI SEO Fan-Out Query Tool")
st.markdown("""
This tool uses Google Gemini **Grounding (Google Search)** to capture the actual search queries the model performs.
Upload a list of prompts to discover what the AI *actually* searches for to answer them.
""")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    # 1. Country Selection (Target Market)
    target_country = st.selectbox(
        "Target Market",
        options=["Denmark", "Norway", "Sweden", "Finland"],
        index=0,
        help="Select the target country to optimize the fan-out context."
    )
    
    st.divider()
    
    # 2. Smart API Key Detection
    # Priority: 1. Streamlit Secrets (Cloud/Local) -> 2. Environment Var -> 3. Manual Input
    
    # Check for the key in Streamlit Secrets or Environment
    api_key_found = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

    if api_key_found:
        # Strict Validation
        api_key = api_key_found.strip()
             
        st.success("✅ API Key active from Secrets/Env.")
        
    else:
        # Only show the input box if no secret is detected
        st.warning("🔑 No API Key found in Secrets.")
        api_key_input = st.text_input("Enter Google API Key manually", type="password")
        
        if api_key_input:
             api_key = api_key_input.strip()
        else:
             api_key = None
             st.info("Please provide an API Key to enable the 'Generate' button.")

    st.divider()
    st.caption("v1.2 | Powered by Gemini 3 Flash")

# Main content
tab1, tab2 = st.tabs(["📂 Upload CSV", "✍️ Manual Input"])

df = None
target_col = None

with tab1:
    uploaded_file = st.file_uploader("Upload CSV file (must contain a 'prompts' or 'Primary Prompt' column)", type=['csv'])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            
            # Column detection
            possible_cols = ['prompts', 'Primary Prompt', 'Prompt', 'query', 'keyword']
            for col in possible_cols:
                if col in df.columns:
                    target_col = col
                    break
            
            if target_col is None:
                target_col = df.columns[0]
                st.info(f"Could not find standard column name. Using content from first column: '{target_col}'")
                
            st.write(f"Loaded **{len(df)}** prompts from column: `{target_col}`")
            
        except Exception as e:
            st.error(f"Error processing file: {e}")

with tab2:
    manual_text = st.text_area("Enter prompts (one per line):", height=200, placeholder="Best investments 2026\nBillig strøm")
    if manual_text:
        prompts = [p.strip() for p in manual_text.split('\n') if p.strip()]
        if prompts:
            df = pd.DataFrame({"Manual Prompt": prompts})
            target_col = "Manual Prompt"
            st.write(f"Parsed **{len(df)}** prompts.")

if df is not None:
    # Preview the data
    st.write("### Data Preview")
    st.dataframe(df.head(), use_container_width=True)
    
    # Validation: Ensure we have a key before allowing processing
    # We strip spaces to make sure it's not just an empty string
    is_ready = api_key and len(api_key.strip()) > 10

    if st.button("Generate Fan-Out Queries", type="primary", disabled=not is_ready):
        results = []  # Initialize results list
        
        with st.status(f"Processing prompts for **{target_country}**...", expanded=True) as status:
            try:
                # 1. Initialize Client using the api_key discovered in the sidebar
                client = fan_out_logic.get_client(api_key)
                
                prompts_list = df[target_col].tolist()
                total = len(prompts_list)
                progress_bar = st.progress(0)
                
                for i, prompt in enumerate(prompts_list):
                    st.write(f"🔍 Analyzing: **{prompt}**")
                    
                    # 2. Call the logic function with the client and target country
                    data = fan_out_logic.generate_fan_out_queries(
                        client, 
                        prompt, 
                        target_country=target_country
                    )
                    
                    if "error" in data:
                        # Handle specific error cases (like rate limits)
                        err_msg = data["error"]
                        st.error(f"Error for '{prompt}': {err_msg}")
                        row = {"Primary Prompt": prompt, "Raw Search Queries": f"ERROR: {err_msg}"}
                    else:
                        # 3. Format the list of queries for the UI/Excel
                        queries = data.get("raw_queries", [])
                        if queries:
                            formatted_queries = "\n".join([f"• {q}" for q in queries])
                        else:
                            formatted_queries = "No specific search queries triggered (AI answered from internal knowledge)."
                        
                        row = {"Primary Prompt": prompt, "Raw Search Queries": formatted_queries}
                    
                    results.append(row)
                    
                    # Update Progress
                    progress_bar.progress((i + 1) / total)
                    
                    # 4. Small delay to respect Gemini Free Tier Rate Limits (15 RPM)
                    # If you have a paid tier, you can reduce this to 0.1
                    import time
                    time.sleep(2.0)
                
                status.update(label="✅ Analysis Complete!", state="complete", expanded=False)
                
            except Exception as e:
                st.error(f"Critical System Error: {e}")
        
        # --- Display and Download Results ---
        if results:
            result_df = pd.DataFrame(results)
            st.divider()
            st.subheader("📊 Fan-Out Results")
            
            # Interactive Results View
            for _, row in result_df.iterrows():
                with st.expander(f"Prompt: {row['Primary Prompt']}", expanded=False):
                    st.markdown(row["Raw Search Queries"])
            
            # Excel Download Section
            st.write("---")
            try:
                import io
                buffer = io.BytesIO()
                # We use openpyxl as the engine for .xlsx files
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    result_df.to_excel(writer, index=False, sheet_name='SEO Fan-Out')
                
                st.download_button(
                    label="📥 Download Results for Excel (.xlsx)",
                    data=buffer.getvalue(),
                    file_name=f"seo_fanout_{target_country.lower()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            except Exception as download_err:
                st.error(f"Could not generate Excel file: {download_err}")
                # Fallback to CSV if Excel fails
                st.download_button(
                    label="📥 Download Results as CSV",
                    data=result_df.to_csv(index=False).encode('utf-8'),
                    file_name=f"seo_fanout_{target_country.lower()}.csv",
                    mime="text/csv",
                )

    elif not is_ready:
        st.warning("Please provide a valid Gemini API Key in the sidebar to start.")
    else:
        st.info("Configuration set! Click 'Generate' to start the Fan-Out analysis.")

else:
    # Initial State when no data is provided
    st.info("👆 Please upload a CSV or enter prompts manually in the tabs above.")