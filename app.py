import streamlit as st
import pandas as pd
import fan_out_logic
import os
import io
from google import genai
import time

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
    
    # FEATURE 1: COUNTRY PERSONA
    # Define Personas
    country_personas = {
        "Denmark": "Du er en voksen forbruger i Danmark. Du søger på dansk og forventer svar der er relevante for det danske marked.",
        "Sweden": "Du är en vuxen konsument i Sverige. Du söker på svenska och förväntar dig svar som är relevanta för den svenska marknaden.",
        "Norway": "Du er en voksen forbruger i Norge. Du søker på norsk og forventer svar som er relevante for det norske markedet.",
        "Finland": "Olet aikuinen kuluttaja Suomessa. Haet suomeksi ja odotat vastauksia, jotka ovat relevantteja Suomen markkinoille."
    }
    
    current_persona = country_personas.get(target_country)
    if current_persona:
        st.info(f"**active persona:**\n\n_{current_persona}_")

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
    st.caption("v1.3 | Powered by Gemini 3 Flash")

# Main content
st.write("---")
# FEATURE 2: BRAND MENTION TRACKER (Input)
brand_input = st.text_input("Brand/Domain to Watch (Optional)", help="Enter comma-separated brands to track in search queries (e.g., 'lego, maersk').")
tracking_brands = [b.strip().lower() for b in brand_input.split(',')] if brand_input else []

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

    # Initialize session state for results
    if 'fanout_results' not in st.session_state:
        st.session_state['fanout_results'] = None

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
                    
                    # 2. Call the logic function with the client and target country AND PERSONA
                    data = fan_out_logic.generate_fan_out_queries(
                        client, 
                        prompt, 
                        target_country=target_country,
                        persona_instruction=country_personas.get(target_country) # FEATURE 1: Pass Persona
                    )
                    
                    if "error" in data:
                        # Handle specific error cases (like rate limits)
                        err_msg = data["error"]
                        st.error(f"Error for '{prompt}': {err_msg}")
                        row = {
                            "Primary Prompt": prompt, 
                            "Raw Search Queries": f"ERROR: {err_msg}",
                            "Classified Data": "[]"
                        }
                    else:
                        # 3. Format the list of queries for the UI/Excel
                        queries = data.get("raw_queries", [])
                        classified = data.get("classified_queries", [])
                        # FEATURE 3: DEEP BRAND ANALYSIS (Share of Search)
                        deep_analysis_data = []
                        if tracking_brands and queries:
                            st.write(f"🕵️‍♀️ Deep Analyzing {len(queries)} sub-queries for brand visibility...")
                            deep_progress = st.progress(0)
                            
                            for d_idx, q in enumerate(queries):
                                # Call deep check
                                deep_res = fan_out_logic.check_brand_visibility(
                                    client, 
                                    q, 
                                    tracking_brands, 
                                    target_country, 
                                    country_personas.get(target_country)
                                )
                                deep_analysis_data.append(deep_res)
                                deep_progress.progress((d_idx + 1) / len(queries))
                                time.sleep(2.0) # Rate limit protection
                            
                            deep_progress.empty()

                        formatted_queries = "\n".join(queries) if queries else "No specific search queries triggered (AI answered from internal knowledge)."
                        
                        import json
                        classified_data_str = json.dumps(classified)
                        deep_data_str = json.dumps(deep_analysis_data)
                        
                        row = {
                            "Primary Prompt": prompt, 
                            "Raw Search Queries": formatted_queries,
                            "Classified Data": classified_data_str,
                            "Deep Data": deep_data_str
                        }
                    
                    results.append(row)
                    
                    # Update Progress
                    progress_bar.progress((i + 1) / total)
                    
                    # 4. Small delay to respect Gemini Free Tier Rate Limits (15 RPM)
                    import time
                    time.sleep(2.0)
                
                status.update(label="✅ Analysis Complete!", state="complete", expanded=False)
                
                # Store in Session State
                st.session_state['fanout_results'] = pd.DataFrame(results)
                
            except Exception as e:
                st.error(f"Critical System Error: {e}")
        
    # --- Display and Analyze Results (Runs on every rerun if data exists) ---
    if st.session_state['fanout_results'] is not None:
        result_df = st.session_state['fanout_results']
        
        # FEATURE 3: DEEP BRAND ANALYSIS (Display)
        if tracking_brands:
            st.divider()
            st.subheader("🎯 Deep Brand Analysis (Share of Search)")
            
            all_brand_hits = []
            
            for _, row in result_df.iterrows():
                prompt = row.get("Primary Prompt", "")
                try:
                    import json
                    deep_data = json.loads(row.get("Deep Data", "[]"))
                except:
                    deep_data = []

                for item in deep_data:
                    if item.get("mentioned"):
                        all_brand_hits.append({
                            "Primary Prompt": prompt,
                            "Fan-out Query": item.get("query"),
                            "Brands Found": ", ".join(item.get("brands_found", [])),
                            "Snippet": item.get("snippet", ""),
                            "Full Response": item.get("full_response", "")
                        })
            
            if all_brand_hits:
                hits_df = pd.DataFrame(all_brand_hits)
                
                # Metrics
                total_queries_generated = sum([len(str(r).split('\n')) for r in result_df["Raw Search Queries"] if "ERROR" not in str(r)])
                total_hits = len(hits_df)
                
                # Share of Search Calculation
                share_of_search = (total_hits / total_queries_generated * 100) if total_queries_generated > 0 else 0
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Brand Mentions", total_hits)
                c2.metric("Share of Search", f"{share_of_search:.1f}%")
                c3.metric("Queries Analyzed", total_queries_generated)
                
                st.markdown("""
                <style>
                .response-box {
                    background-color: var(--secondary-background-color);
                    border: 1px solid rgba(49, 51, 63, 0.2);
                    border-radius: 8px;
                    padding: 15px;
                    max-height: 400px;
                    overflow-y: auto;
                    font-size: 14px;
                    line-height: 1.6;
                    white-space: pre-wrap; /* Preserves newlines */
                    margin-top: 5px;
                }
                /* Dark mode border adjustment */
                @media (prefers-color-scheme: dark) {
                    .response-box {
                        border: 1px solid rgba(250, 250, 250, 0.2);
                    }
                }
                /* Custom Scrollbar */
                .response-box::-webkit-scrollbar {
                    width: 10px;
                }
                .response-box::-webkit-scrollbar-track {
                    background: rgba(0,0,0,0.05);
                    border-radius: 5px;
                }
                .response-box::-webkit-scrollbar-thumb {
                    background-color: rgba(100, 100, 100, 0.5);
                    border-radius: 5px;
                    border: 2px solid transparent;
                    background-clip: content-box;
                }
                .response-box::-webkit-scrollbar-thumb:hover {
                    background-color: rgba(100, 100, 100, 0.8);
                }
                </style>
                """, unsafe_allow_html=True)

                st.subheader("📝 Detailed Mentions")
                for i, hit in enumerate(all_brand_hits):
                    with st.expander(f"Mention #{i+1}: {hit['Fan-out Query']} ({hit['Brands Found']})"):
                        st.info(f"**Context Snippet:** ...{hit['Snippet']}...", icon="🔎")
                        st.markdown("**Full AI Answer:**")
                        full_resp = hit.get("Full Response", "No text stored.")
                        # Escape HTML just in case
                        import html
                        safe_resp = html.escape(full_resp)
                        st.markdown(f'<div class="response-box">{safe_resp}</div>', unsafe_allow_html=True)
                
                # Download for Brand Hits
                # Drop Full Response from CSV to keep it clean, or keep it? User might want it. I'll keep it.
                csv_hits = hits_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Brand Tracker Results (CSV)",
                    data=csv_hits,
                    file_name=f"brand_tracker_{target_country.lower()}.csv",
                    mime="text/csv"
                )
            else:
                st.info(f"No mentions of **{', '.join(tracking_brands)}** found in the AI answers for generated queries.")

        st.divider()
        st.subheader("📊 Fan-Out Results")
        
        # Custom CSS for Cards
        st.markdown("""
        <style>
        .fanout-card {
            background-color: var(--secondary-background-color);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            border: 1px solid var(--text-color-20);
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .fanout-query {
            font-size: 16px;
            font-weight: 500;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .intent-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 10px;
        }
        .intent-commercial { background-color: #fef08a; color: #854d0e; }
        .intent-informational { background-color: #dbeafe; color: #1e40af; }
        .intent-transactional { background-color: #dcfce7; color: #166534; }
        .intent-navigational { background-color: #f3e8ff; color: #6b21a8; }
        .brand-hit {
            background-color: #ffedd5;
            border: 1px solid #f97316;
            color: #c2410c;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 700;
        }
        .main-prompt-box {
            background-color: var(--primary-background-color);
            border-left: 4px solid #ff4b4b;
            padding: 10px;
            margin-bottom: 15px;
        }
        </style>
        """, unsafe_allow_html=True)

        # Interactive Results View
        for _, row in result_df.iterrows():
            with st.expander(f"Prompt: {row['Primary Prompt']}", expanded=True):
                
                # Display Main Prompt
                st.markdown(f"""
                <div class="main-prompt-box">
                    <small>Main Prompt</small><br>
                    <strong>{row['Primary Prompt']}</strong>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("### 🔍 Fan-Out Queries")
                
                # Parse Data
                try:
                    import json
                    classified_data = json.loads(row.get("Classified Data", "[]"))
                    deep_data = json.loads(row.get("Deep Data", "[]"))
                except:
                    classified_data = []
                    deep_data = []

                if classified_data:
                    for item in classified_data:
                        intent = item.get("intent", "Unknown")
                        query = item.get("query", "")
                        icon = item.get("icon", "⚪")
                        
                        # Match with Deep Data
                        brand_badge = ""
                        deep_match = next((d for d in deep_data if d.get("query") == query), None)
                        if deep_match and deep_match.get("mentioned"):
                             brands_str = ", ".join(deep_match.get("brands_found", []))
                             brand_badge = f'<span class="brand-hit">🔥 {brands_str} Detected</span>'
                        
                        # Map intent to CSS class
                        css_class = "intent-informational"
                        if "Commercial" in intent: css_class = "intent-commercial"
                        elif "Transactional" in intent: css_class = "intent-transactional"
                        elif "Navigational" in intent: css_class = "intent-navigational"

                        st.markdown(f"""
                        <div class="fanout-card">
                            <div class="fanout-query">
                                <span><span class="intent-badge {css_class}">{icon} {intent}</span> {query}</span>
                                {brand_badge}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                else:
                    # Fallback to simple list if classification failed
                    raw_text = row["Raw Search Queries"]
                    if raw_text:
                        queries = raw_text.split('\n')
                        for q in queries:
                            if "No specific search" not in q:
                                st.info(q, icon="🔎")
                            else:
                                st.warning(raw_text)
                    else:
                        st.warning("No data found.")
        
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