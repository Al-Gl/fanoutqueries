import streamlit as st
import pandas as pd
import fan_out_logic
import os
import io
from google import genai
import time
import json
import altair as alt
import pdf_generator

# --- CONFIGURATION & STATE ---
st.set_page_config(page_title="Fan-Out Query Tool", page_icon="🕸️", layout="wide")

if 'page' not in st.session_state:
    st.session_state['page'] = 'home'

if 'fanout_results' not in st.session_state:
    st.session_state['fanout_results'] = None

if 'inputs' not in st.session_state:
    st.session_state['inputs'] = {}

# --- HELPER FUNCTIONS ---
def initialize_client():
    """Retrieves API Key."""
    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        # Check session state input if manual entry
        api_key = st.session_state.get('manual_api_key')
    
    if not api_key:
        return None
    return genai.Client(api_key=api_key.strip())

# --- VIEWS ---

def render_home():
    """Renders the Centered Start Page."""
    # Custom CSS for Start Page
    st.markdown("""
    <style>
    .stApp {
        background-color: var(--primary-background-color);
    }
    .main-container {
        max-width: 800px;
        margin: 0 auto;
        padding-top: 60px;
        text-align: center;
    }
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-size: 3.5rem;
        font-weight: 800;
        margin-bottom: 10px;
        background: linear-gradient(90deg, #FF4B4B, #FF9068);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
    }
    @media (prefers-color-scheme: dark) {
        .hero-title {
             background: linear-gradient(90deg, #FF4B4B, #FF9068);
             -webkit-background-clip: text;
             -webkit-text-fill-color: transparent;
        }
    }
    .hero-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 1.25rem;
        color: var(--text-color-80);
        margin-bottom: 50px;
        font-weight: 400;
    }
    
    /* Input Styling Enhancements */
    /* Streamlit's default inputs are decent, but we can enhance labels */
    .stTextInput > label, .stTextArea > label, .stSelectbox > label {
        font-weight: 600;
        letter-spacing: 0.5px;
        color: var(--text-color);
    }
    
    /* Button Customization */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #FF4B4B 0%, #FF9068 100%);
        color: white;
        font-weight: 700;
        border: none;
        padding: 0.6rem 2rem;
        border-radius: 8px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 14px 0 rgba(255, 75, 75, 0.39);
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px 0 rgba(255, 75, 75, 0.23);
    }

    /* Glassmorphism for Container */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        st.markdown('<h1 class="hero-title">Fan-Out Query Explorer</h1>', unsafe_allow_html=True)
        st.markdown('<p class="hero-subtitle">Map the search landscape. Track your brand. Dominate the results.</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Input Form
        c1, c2, c3 = st.columns([1, 6, 1]) # Wider center column
        with c2:
            with st.container(border=True):
                st.subheader("🛠️ Configure Analysis")
                st.markdown("---")
                
                # 1. API Key (if needed) - Minimal UI
                client = initialize_client()
                if not client:
                    manual_key = st.text_input("Enter Google API Key", type="password", key="manual_api_key_input")
                    if manual_key:
                        st.session_state['manual_api_key'] = manual_key
                        st.rerun()
                    st.warning("Please enter API Key to proceed.")
                    st.stop()
                
                # 2. Market & Persona
                target_country = st.selectbox(
                    "Target Market",
                    options=["Denmark", "Norway", "Sweden", "Finland"],
                    index=["Denmark", "Norway", "Sweden", "Finland"].index(st.session_state['inputs'].get('target_country', 'Denmark'))
                )

                # 3. Brand Tracking
                c_brand, c_comp = st.columns(2)
                with c_brand:
                    primary_brand = st.text_input("My Brand (Optional)", value=st.session_state['inputs'].get('primary_brand', ''), placeholder="e.g. Lego")
                with c_comp:
                    competitors_str = st.text_input("Competitors (Max 5)", value=st.session_state['inputs'].get('competitors', ''), placeholder="e.g. Playmobil, Barbie")

                # 4. Prompt Input
                prompt_text = st.text_area(
                    "Search Topic / Keywords", 
                    height=120, 
                    value=st.session_state['inputs'].get('prompt', ''),
                    placeholder="Enter keywords or topics (one per line)..."
                )

                st.markdown("<br>", unsafe_allow_html=True)
                
                # Action Button
                if st.button("🚀 Analyze Market", type="primary", use_container_width=True):
                    if not prompt_text:
                        st.error("Please enter at least one topic.")
                    else:
                        st.session_state['inputs'] = {
                            'target_country': target_country,
                            'primary_brand': primary_brand,
                            'competitors': competitors_str,
                            'prompt': prompt_text
                        }
                        st.session_state['page'] = 'processing'
                        st.rerun()

def render_processing():
    """Renders the Full-Screen Loading Transition and runs Logic."""
    
    # CSS for Overlay + Progress Bar
    st.markdown("""
    <style>
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: var(--primary-background-color);
        z-index: 999999;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .spinner {
        width: 50px;
        height: 50px;
        border: 5px solid rgba(0,0,0,0.1);
        border-radius: 50%;
        border-top-color: #ff4b4b;
        animation: spin 1s ease-in-out infinite;
        margin-bottom: 20px;
    }
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    .loading-text {
        font-size: 1.5rem;
        font-weight: 500;
        color: var(--text-color);
        animation: pulse 1.5s infinite;
        margin-bottom: 10px;
    }
    @keyframes pulse {
        0% { opacity: 0.6; }
        50% { opacity: 1; }
        100% { opacity: 0.6; }
    }
    .progress-container {
        width: 300px;
        height: 8px;
        background-color: rgba(128,128,128,0.2);
        border-radius: 4px;
        overflow: hidden;
    }
    .progress-bar {
        width: 0%;
        height: 100%;
        background-color: #ff4b4b;
        transition: width 0.3s ease;
    }
    </style>
    <div class="loading-overlay">
        <div class="spinner"></div>
        <div class="loading-text" id="loading-msg">Initializing Agent...</div>
        <div class="progress-container">
            <div class="progress-bar" id="pb"></div>
        </div>
    </div>
    <script>
    const msgs = ["Scanning search intent...", "Identifying competitors...", "Generating fan-out queries...", "Calculating share of voice...", "Finalizing report..."];
    let i = 0;
    setInterval(() => {
        const el = document.getElementById('loading-msg');
        if(el) {
            el.innerText = msgs[i % msgs.length];
            i++;
        }
    }, 2000);
    </script>
    """, unsafe_allow_html=True)
    
    # --- EXECUTE LOGIC ---
    try:
        inputs = st.session_state['inputs']
        target_country = inputs['target_country']
        primary_brand = inputs['primary_brand'].strip() if inputs['primary_brand'] else None
        competitors = [c.strip() for c in inputs['competitors'].split(',') if c.strip()][:5]
        prompts = [p.strip() for p in inputs['prompt'].split('\n') if p.strip()]
        
        tracking_brands = []
        if primary_brand: tracking_brands.append(primary_brand)
        tracking_brands.extend(competitors)
        tracking_brands = list(set(tracking_brands))
        
        # Store explicit list for dashboard
        st.session_state['tracking_config'] = {
            'primary_brand': primary_brand,
            'competitors': competitors,
            'tracking_brands': tracking_brands
        }

        # Define Personas
        country_personas = {
            "Denmark": "Du er en voksen forbruger i Danmark. Du søger på dansk og forventer svar der er relevante for det danske marked.",
            "Sweden": "Du är en vuxen konsument i Sverige. Du söker på svenska och förväntar dig svar som är relevanta för den svenska marknaden.",
            "Norway": "Du er en voksen forbruger i Norge. Du søker på norsk og forventer svar som er relevante for det norske markedet.",
            "Finland": "Olet aikuinen kuluttaja Suomessa. Haet suomeksi ja odotat vastauksia, jotka ovat relevantteja Suomen markkinoille."
        }
        
        client = initialize_client()
        if not client:
             raise ValueError("API Key not found.")

        results = []
        total_steps = len(prompts)
        
        if total_steps == 0:
            st.warning("No valid prompts found.")
            st.markdown('<style>.loading-overlay { display: none; }</style>', unsafe_allow_html=True)
            if st.button("Go Back"):
                st.session_state['page'] = 'home'
                st.rerun()
            return

        # Logic Loop
        for i, prompt in enumerate(prompts):
            # Base progress for this item
            base_scan_pct = (i / total_steps) * 100
            
            # 1. Initial State for this prompt (show activity)
            st.markdown(f"""<style>#pb {{ width: {base_scan_pct + 2}% !important; }}</style>""", unsafe_allow_html=True)
            
            try:
                # 1. Fan Out
                data = fan_out_logic.generate_fan_out_queries(
                    client, prompt, target_country=target_country, 
                    persona_instruction=country_personas.get(target_country)
                )
                
                if "error" in data:
                    row = {"Primary Prompt": prompt, "Raw Search Queries": f"ERROR: {data['error']}", "Deep Data": "[]"}
                else:
                    queries = data.get("raw_queries", [])
                    classified = data.get("classified_queries", [])
                    
                    # Update: Fan-out done, starting Deep Analysis
                    # Jump forward a bit within this item's slice
                    start_deep_pct = base_scan_pct + ((1 / total_steps) * 20) # 20% of this item
                    st.markdown(f"""<style>#pb {{ width: {start_deep_pct}% !important; }}</style>""", unsafe_allow_html=True)
                    
                    # 2. Deep Analysis
                    deep_analysis_data = []
                    if tracking_brands and queries:
                        num_queries = len(queries)
                        # We allocate the remaining 80% of this item's progress to the deep loop
                        item_slice = (1 / total_steps) * 80 
                        
                        for q_idx, q in enumerate(queries):
                            deep_res = fan_out_logic.check_brand_visibility(
                                client, q, tracking_brands, target_country, country_personas.get(target_country)
                            )
                            deep_analysis_data.append(deep_res)
                            
                            # Granular Update
                            current_sub_pct = start_deep_pct + (item_slice * ((q_idx + 1) / num_queries))
                            st.markdown(f"""<style>#pb {{ width: {current_sub_pct}% !important; }}</style>""", unsafe_allow_html=True)
                            
                            time.sleep(0.5) # Faster sleep for UX

                    row = {
                        "Primary Prompt": prompt,
                        "Raw Search Queries": "\n".join(queries),
                        "Classified Data": json.dumps(classified),
                        "Deep Data": json.dumps(deep_analysis_data)
                    }
                results.append(row)
            except Exception as e:
                st.error(f"Error processing {prompt}: {e}")
                
        # Final 100%
        st.markdown(f"""<style>#pb {{ width: 100% !important; }}</style>""", unsafe_allow_html=True)
        time.sleep(0.5) 
                
        # Save Results
        st.session_state['fanout_results'] = pd.DataFrame(results)
        
        # Transition to Dashboard
        st.session_state['page'] = 'dashboard'
        st.rerun()

    except Exception as e:
        # CRITICAL: Hide overlay so error is visible
        st.markdown('<style>.loading-overlay { display: none; }</style>', unsafe_allow_html=True)
        st.error(f"⚠️ System Error during processing: {e}")
        if st.button("Return to Home"):
            st.session_state['page'] = 'home'
            st.rerun()

def render_dashboard():
    """Renders the V2 Dashboard."""
    
    # Navbar / Header
    c1, c2 = st.columns([3, 1])
    with c1:
        st.title("🕸️ Market Intelligence Dashboard")
    with c2:
        if st.button("← New Analysis"):
            st.session_state['page'] = 'home'
            st.rerun()
    
    result_df = st.session_state['fanout_results']
    config = st.session_state.get('tracking_config', {})
    primary_brand = config.get('primary_brand')
    competitors = config.get('competitors', [])
    tracking_brands = config.get('tracking_brands', [])
    
    if result_df is None or result_df.empty:
        st.warning("No results found.")
        return

    # --- DASHBOARD LOGIC (From V2) ---
    # 1. Market Share Dashboard
    if tracking_brands:
        st.divider()
        
        # Calculation
        all_brand_hits = []
        brand_counts = {b: 0 for b in tracking_brands}
        total_queries_analyzed = 0
        
        for _, row in result_df.iterrows():
            try:
                deep_data = json.loads(row.get("Deep Data", "[]"))
            except:
                deep_data = []
            
            total_queries_analyzed += len(deep_data)

            for item in deep_data:
                found = item.get("brands_found", [])
                if found:
                    found_lower = [f.lower() for f in found]
                    for tracked in tracking_brands:
                        if any(tracked.lower() in f for f in found_lower): 
                            brand_counts[tracked] += 1
                    
                    is_primary = False
                    if primary_brand:
                         is_primary = any(primary_brand.lower() in f for f in found_lower)

                    all_brand_hits.append({
                        "Primary Prompt": row.get("Primary Prompt", ""),
                        "Fan-out Query": item.get("query"),
                        "Brands Found": ", ".join(found),
                        "Snippet": item.get("snippet", ""),
                        "Full Response": item.get("full_response", ""),
                        "Type": "✅ You" if is_primary else "⚠️ Competitor"
                    })
        
        # UI
        st.subheader("📊 Market Share Dashboard")
        k1, k2, k3 = st.columns(3)
        my_count = brand_counts.get(primary_brand, 0) if primary_brand else 0
        comp_count = sum(brand_counts.get(c, 0) for c in competitors)
        sov_you = (my_count / total_queries_analyzed * 100) if total_queries_analyzed > 0 else 0
        sov_comp = (comp_count / total_queries_analyzed * 100) if total_queries_analyzed > 0 else 0
        
        k1.metric("Your Share of Voice", f"{sov_you:.1f}%", f"{my_count} mentions")
        k2.metric("Competitor Share", f"{sov_comp:.1f}%", f"{comp_count} mentions")
        k3.metric("Total Opportunities", total_queries_analyzed)
        
        st.markdown("### Branding Landscape")
        if total_queries_analyzed > 0 and any(brand_counts.values()):
            # Prepare data for Altair
            source = pd.DataFrame({
                "Brand": list(brand_counts.keys()),
                "Mentions": list(brand_counts.values()),
                "Type": ["You" if b == primary_brand else "Competitor" for b in brand_counts.keys()]
            })
            
            c_chart1, c_chart2 = st.columns(2)
            
            with c_chart1:
                st.caption("Share of Mentions")
                # Donut Chart
                base = alt.Chart(source).encode(theta=alt.Theta("Mentions", stack=True))
                pie = base.mark_arc(outerRadius=100, innerRadius=60).encode(
                    color=alt.Color("Brand", scale=alt.Scale(scheme="category10")),
                    order=alt.Order("Mentions", sort="descending"),
                    tooltip=["Brand", "Mentions", "Type"]
                )
                text = base.mark_text(radius=130).encode(
                    text=alt.Text("Mentions"),
                    order=alt.Order("Mentions", sort="descending"),
                    color=alt.value("var(--text-color)")  
                )
                st.altair_chart(pie + text, use_container_width=True)
            
            with c_chart2:
                st.caption("Mentions by Brand")
                # Horizontal Bar
                bars = alt.Chart(source).mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3).encode(
                    x=alt.X('Mentions', axis=None),
                    y=alt.Y('Brand', sort='-x', axis=alt.Axis(title=None, labelFontSize=12)),
                    color=alt.Color('Type', scale=alt.Scale(domain=['You', 'Competitor'], range=['#16a34a', '#dc2626']), legend=None),
                    tooltip=['Brand', 'Mentions']
                )
                
                text_bar = bars.mark_text(
                    align='left',
                    baseline='middle',
                    dx=3 
                ).encode(
                    text='Mentions'
                )
                
                st.altair_chart((bars + text_bar).properties(height=300), use_container_width=True)
        else:
            if total_queries_analyzed > 0:
                st.info("No brand mentions detected in the analyzed queries.")

        # Detailed List
        st.subheader("📝 Detailed Surveillance")
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
            white-space: pre-wrap;
            margin-top: 5px;
        }
        .hit-tag-you { background-color: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
        .hit-tag-comp { background-color: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
        </style>
        """, unsafe_allow_html=True)

        if not all_brand_hits:
                st.info(f"No mentions of **{', '.join(tracking_brands)}** found.")
        else:
            for i, hit in enumerate(all_brand_hits):
                tag_class = "hit-tag-you" if "You" in hit["Type"] else "hit-tag-comp"
                label_icon = "🟢" if "You" in hit["Type"] else "🔴"
                with st.expander(f"{label_icon} {hit['Type']} detected in query: {hit['Fan-out Query']}"):
                    st.caption(f"Brands Found: {hit['Brands Found']}")
                    st.info(f"**Context Snippet:** ...{hit['Snippet']}...", icon="🔎")
                    st.markdown("**Full AI Answer:**")
                    import html
                    safe_resp = html.escape(hit.get("Full Response", ""))
                    st.markdown(f'<div class="response-box">{safe_resp}</div>', unsafe_allow_html=True)
            
            # Download
            csv_hits = pd.DataFrame(all_brand_hits).to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Surveillance Report (CSV)", csv_hits, "brand_surveillance.csv", "text/csv")

    st.divider()
    st.subheader("🔍 Expanded Search Intent")
    
    # Fan Out Cards CSS
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
    .intent-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 5px;
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
        margin-left: auto;
    }
    .main-prompt-box {
        background-color: var(--primary-background-color);
        border-left: 4px solid #ff4b4b;
        padding: 10px;
        margin-bottom: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

    for _, row in result_df.iterrows():
        with st.expander(f"Prompt: {row['Primary Prompt']}", expanded=True):
            st.markdown(f'<div class="main-prompt-box"><small>Main Prompt</small><br><strong>{row["Primary Prompt"]}</strong></div>', unsafe_allow_html=True)
            
            try:
                classified_data = json.loads(row.get("Classified Data", "[]"))
                deep_data = json.loads(row.get("Deep Data", "[]"))
            except:
                classified_data, deep_data = [], []

            if classified_data:
                for item in classified_data:
                    intents = item.get("intents", [])
                    icons = item.get("icons", [])
                    query = item.get("query", "")
                    
                    if not intents and "intent" in item:
                        intents = [item["intent"]]
                        icons = [item.get("icon", "⚪")]
                    
                    brand_badge = ""
                    deep_match = next((d for d in deep_data if d.get("query") == query), None)
                    if deep_match and deep_match.get("mentioned"):
                         brands_str = ", ".join(deep_match.get("brands_found", []))
                         brand_badge = f'<span class="brand-hit">🔥 {brands_str} Detected</span>'
                    
                    badges_html = ""
                    for idx, intent in enumerate(intents):
                        icon = icons[idx] if idx < len(icons) else "⚪"
                        css_class = "intent-informational"
                        if "Commercial" in intent: css_class = "intent-commercial"
                        elif "Transactional" in intent: css_class = "intent-transactional"
                        elif "Navigational" in intent: css_class = "intent-navigational"
                        badges_html += f'<span class="intent-badge {css_class}">{icon} {intent}</span>'

                    st.markdown(f"""
                    <div class="fanout-card">
                        <div style="display:flex; align-items:center; justify-content: space-between;">
                            <div style="display:flex; align-items:center; flex-wrap: wrap; gap: 5px;">
                                {badges_html} 
                                <span style="font-weight:500; margin-left: 5px;">{query}</span>
                            </div>
                            {brand_badge}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                 st.info(row["Raw Search Queries"])
    
    # Download All
    st.write("---")
    
    # PDF Export Integration
    if st.button("📄 Export PDF Report"):
        # Prepare Data
        # Calculate totals again for report context
        my_count = brand_counts.get(primary_brand, 0) if primary_brand else 0
        comp_count = sum(brand_counts.get(c, 0) for c in competitors)
        
        sov_you = (my_count / total_queries_analyzed * 100) if total_queries_analyzed > 0 else 0
        sov_comp = (comp_count / total_queries_analyzed * 100) if total_queries_analyzed > 0 else 0
        
        # Prepare Detail List (simplified for PDF)
        detailed_hits = []
        for hit in all_brand_hits:
            detailed_hits.append({
                "type": hit["Type"],
                "query": hit["Fan-out Query"],
                "brands": hit["Brands Found"]
            })
            
        report_data = {
            "target_country": st.session_state['inputs'].get('target_country'),
            "primary_brand": primary_brand,
            "competitors": competitors,
            "metrics": {
                "sov_you": sov_you,
                "sov_comp": sov_comp,
                "you_count": my_count,
                "comp_count": comp_count,
                "total_queries": total_queries_analyzed
            },
            "detailed_hits": detailed_hits
        }
        
        pdf_buffer = pdf_generator.create_pdf_report(report_data)
        st.download_button(
            label="⬇️ Download PDF",
            data=pdf_buffer,
            file_name="market_intelligence_report.pdf",
            mime="application/pdf",
        )

    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            result_df.to_excel(writer, index=False, sheet_name='Search Data')
        st.download_button("📥 Download Search Data (.xlsx)", buffer.getvalue(), "market_intel.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except:
        st.download_button("📥 Download Search Data (CSV)", result_df.to_csv(index=False).encode('utf-8'), "market_intel.csv", "text/csv")


# --- MAIN CONTROL FLOW ---
if st.session_state['page'] == 'home':
    render_home()
elif st.session_state['page'] == 'processing':
    render_processing()
elif st.session_state['page'] == 'dashboard':
    render_dashboard()