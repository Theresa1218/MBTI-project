import streamlit as st
import os
import json
from dotenv import load_dotenv

# Custom Modules
import mbti
import charts
import agent

load_dotenv()

# ==========================================
# 1. Page Config & CUTE Theme
# ==========================================
st.set_page_config(page_title="🎄 MBTI North Pole", layout="wide")

def set_cute_theme():
    st.markdown("""
    <style>
    .stApp {
        background-color: #3B6255;
        background-image: linear-gradient(180deg, #3B6255 0%, #1a2e1a 100%);
        color: #fff;
    }
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.15);
        border: 2px solid #8B0000;
        border-radius: 20px;
    }
    .stButton > button {
        background-color: #8B0000 !important;
        color: white !important;
        font-weight: bold;
        border: none;
        border-radius: 15px;
        border-top: 6px solid white !important;
        box-shadow: 0px 4px 0px #500000;
    }
    .stButton > button:hover {
        transform: translateY(2px);
        box-shadow: 0px 2px 0px #500000;
        background-color: #a00000 !important;
    }
    @keyframes snow {
        0% { transform: translateY(-10px); opacity: 0; }
        20% { opacity: 1; }
        100% { transform: translateY(100vh); opacity: 0.3; }
    }
    .snowflake {
        position: fixed; top: -10%;
        animation: snow 10s linear infinite;
        color: #fff; pointer-events: none; z-index: 9999;
        font-size: 1.5em;
    }
    </style>
    <div class="snowflake" style="left:10%">❄️</div>
    <div class="snowflake" style="left:30%; animation-delay:2s">❅</div>
    <div class="snowflake" style="left:50%; animation-delay:4s">❆</div>
    <div class="snowflake" style="left:70%; animation-delay:1s">❄️</div>
    <div class="snowflake" style="left:90%; animation-delay:5s">❅</div>
    """, unsafe_allow_html=True)

set_cute_theme()

# ==========================================
# 2. Sidebar Settings
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/christmas-penguin.png", width=80)
    st.header("⚙️ North Pole Settings")
    connection_type = st.radio("AI Helper", ["Remote NCKU", "Local Ollama"])

    if connection_type == "Remote NCKU":
        api_base = os.getenv("API_BASE_URL")
        api_key = os.getenv("API_KEY")
        if not api_key: api_key = st.text_input("Secret Key", type="password")
        model_name = "gemma3:4b"
    else:
        api_base = os.getenv("LOCAL_OLLAMA_URL", "http://localhost:11434")
        api_key = "ollama"
        model_name = "llama3.2:1b"

    st.markdown("---")
    if st.button("🗑️ Start Fresh"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 3. State Initialization
# ==========================================
if "parsed_speakers" not in st.session_state: st.session_state.parsed_speakers = {}
if "analysis_results" not in st.session_state: st.session_state.analysis_results = None
if "chat_messages" not in st.session_state: st.session_state.chat_messages = []
# We now store a dictionary of charts
if "charts_data" not in st.session_state: st.session_state.charts_data = None 

# ==========================================
# 4. Main UI
# ==========================================
st.title("🎅 AI MBTI Workshop")
st.markdown("### *Analyzing personalities, one chat at a time!*")

uploaded_file = st.file_uploader("📂 Drop your chat file here", type=['txt'])

# Welcome Message
if not uploaded_file and not st.session_state.analysis_results:
    st.info("👋 **Welcome!** Upload a chat history to get started. 🎁")

if uploaded_file and api_base:
    if not st.session_state.parsed_speakers:
        content = uploaded_file.getvalue().decode("utf-8")
        st.session_state.parsed_speakers = mbti.parse_line_chat_dynamic(content)

    if st.session_state.parsed_speakers:
        speakers = st.session_state.parsed_speakers
        names = list(speakers.keys())
        
        if not st.session_state.analysis_results:
            st.markdown("### 👥 Who is on the list?")
            selected = st.multiselect("Pick friends:", names, default=names)
            
            if st.button("🚀 Run Analysis"):
                if not selected:
                    st.warning("Pick someone!")
                else:
                    with st.spinner("🦌 Crunching numbers..."):
                        data = {n: speakers[n] for n in selected}
                        sys_prompt, user_content = mbti.construct_analysis_prompt(data)
                        res = agent.run_analysis_request(sys_prompt, user_content, api_key, api_base, model_name)
                        
                        if res and "results" in res:
                            st.session_state.analysis_results = res["results"]
                            st.session_state.chat_messages = []
                            st.session_state.charts_data = None # Reset charts
                            
                            intro_msg = f"**Analysis Complete!** 🎄\n"
                            for p in res["results"]:
                                intro_msg += f"\n* **{p['name']}**: `{p['mbti']}`"
                            st.session_state.chat_messages.append({"role": "assistant", "content": intro_msg})
                            st.rerun()
                        else:
                            st.error("Analysis Failed.")

# ==========================================
# 5. Results & Chat
# ==========================================
if st.session_state.analysis_results:
    st.markdown("---")
    
    # --- CHART SECTION (UPDATED) ---
    if st.session_state.charts_data:
        st.subheader("📊 Visualizations")
        # Tabs for multiple graph types
        tab1, tab2, tab3 = st.tabs(["✨ Spectrum", "📊 Bar Chart", "🕸️ Radar"])
        with tab1:
            st.plotly_chart(st.session_state.charts_data['spectrum'], use_container_width=True)
        with tab2:
            st.plotly_chart(st.session_state.charts_data['bar'], use_container_width=True)
        with tab3:
            st.plotly_chart(st.session_state.charts_data['radar'], use_container_width=True)

    # Chat History
    st.markdown("### 💬 Chat with Elf")
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    if prompt := st.chat_input("Ask about compatibility..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                resp_text, _ = agent.generate_chat_response(
                    prompt, st.session_state.chat_messages, 
                    st.session_state.analysis_results,
                    api_key, api_base, model_name, mbti.is_chinese
                )
                
                if resp_text == "TOOL:CHART":
                    # GENERATE ALL CHARTS
                    results = st.session_state.analysis_results
                    charts_dict = {
                        'spectrum': charts.generate_bipolar_chart(results),
                        'bar': charts.generate_group_bar_chart(results),
                        'radar': charts.generate_radar_chart(results)
                    }
                    st.session_state.charts_data = charts_dict
                    
                    final_msg = "📊 I've painted some charts for you! (See tabs above)"
                    st.markdown(final_msg)
                    st.session_state.chat_messages.append({"role": "assistant", "content": final_msg})
                    st.rerun()
                else:
                    st.markdown(resp_text)
                    st.session_state.chat_messages.append({"role": "assistant", "content": resp_text})

elif not api_base:
    st.warning("⚠️ Please configure AI settings in sidebar.")