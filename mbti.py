import streamlit as st
import json
import re
import plotly.graph_objects as go
from io import StringIO
import requests
import random

API_BASE_URL = "https://api-gateway.netdb.csie.ncku.edu.tw"

# ==========================================
# 1. Session State Initialization
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "agent_chart" not in st.session_state:
    st.session_state.agent_chart = None
if "context_data" not in st.session_state:
    st.session_state.context_data = {}
if "parsed_speakers" not in st.session_state:
    st.session_state.parsed_speakers = {}

# ==========================================
# 2. Logic Helper
# ==========================================
def align_scores_with_mbti(mbti_type, raw_scores):
    """Adjusts scores slightly to ensure they match the assigned MBTI letter."""
    if not mbti_type or len(raw_scores) != 4:
        return [50, 50, 50, 50]
    mbti = mbti_type.upper()
    corrected = list(raw_scores)
    
    # E vs I
    if 'I' in mbti: corrected[0] = min(corrected[0], 45)
    elif 'E' in mbti: corrected[0] = max(corrected[0], 55)
    # S vs N
    if 'S' in mbti: corrected[1] = min(corrected[1], 45)
    elif 'N' in mbti: corrected[1] = max(corrected[1], 55)
    # T vs F
    if 'T' in mbti: corrected[2] = min(corrected[2], 45)
    elif 'F' in mbti: corrected[2] = max(corrected[2], 55)
    # J vs P
    if 'J' in mbti: corrected[3] = min(corrected[3], 45)
    elif 'P' in mbti: corrected[3] = max(corrected[3], 55)
    
    return corrected

def is_chinese(text):
    """Check if input text contains Chinese characters."""
    return bool(re.search(r'[\u4e00-\u9fff]', text))

# ==========================================
# 3. Tools Definition (Updated Parser)
# ==========================================
def parse_line_chat_dynamic(file_content):
    """Parses chat log and returns a dictionary of ALL speakers."""
    lines = file_content.split('\n')
    messages = {}
    
    # Keywords to skip (System messages)
    skip_keywords = [
        "通話時間", "Call time", "Unsend message", "已收回訊息", 
        "joined the chat", "invite", "加入聊天", "invited", "邀請"
    ]
    # Filter out names that are actually system noise
    invalid_names = ["You", "you", "System", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for line in lines:
        line = line.strip()
        if not line: continue

        # 1. Try Tab Split (Standard Line Export)
        parts = line.split('\t')
        
        # 2. If no tabs, try Space Split (Common copy-paste format)
        if len(parts) < 3:
            # Split into max 3 parts: Time, Name, Message
            parts = line.split(' ', 2)

        # Check if we successfully extracted 3 parts (Time, Name, Message)
        if len(parts) >= 3:
            time_str = parts[0]
            name = parts[1].strip()
            msg = parts[2].strip()

            # Validate Time Format (00:00 - 23:59)
            if not re.match(r'^\d{1,2}:\d{2}$', time_str):
                continue
            
            # Clean up Name (Remove "Photos", "Stickers" if mistakenly attached)
            if name.endswith(" Photos"): name = name.replace(" Photos", "")
            if name.endswith(" Stickers"): name = name.replace(" Stickers", "")

            # Skip system messages
            if any(k in msg for k in skip_keywords): continue
            if msg == "[Photos]" or msg == "[Stickers]": continue 
            if name in invalid_names: continue

            if name not in messages: messages[name] = []
            messages[name].append(msg)
            
    # Keep speakers with at least 3 messages
    valid_speakers = {k: "\n".join(v) for k, v in messages.items() if len(v) >= 3}
    return valid_speakers

# 🛠️ Tool 1: Compatibility (Only for exactly 2 people)
def tool_calculate_compatibility(scores_a, scores_b):
    try:
        diff_sum = 0
        for a, b in zip(scores_a, scores_b):
            diff_sum += abs(a - b)
        score = 100 - (diff_sum * 0.25)
        return max(10, min(99, int(score))) 
    except:
        return 50

# 🛠️ Tool 2: Dynamic Bipolar Chart (Supports N people)
def tool_generate_bipolar_chart(analysis_results):
    try:
        dimensions = [
            {"label": "Energy Source", "left": "I (Introversion)", "right": "E (Extraversion)", "y": 0},
            {"label": "Information", "left": "S (Sensing)", "right": "N (Intuition)", "y": 1},
            {"label": "Decisions", "left": "T (Thinking)", "right": "F (Feeling)", "y": 2},
            {"label": "Lifestyle", "left": "J (Judging)", "right": "P (Perceiving)", "y": 3}
        ]
        
        fig = go.Figure()
        
        # Draw the 4 background lines
        for dim in dimensions:
            fig.add_shape(type="line", x0=0, y0=dim['y'], x1=100, y1=dim['y'], line=dict(color="#E0E0E0", width=6))
            fig.add_annotation(x=-8, y=dim['y'], text=dim['left'], showarrow=False, xanchor="right", font=dict(size=14, color="#555"))
            fig.add_annotation(x=108, y=dim['y'], text=dim['right'], showarrow=False, xanchor="left", font=dict(size=14, color="#555"))
        
        # Color palette for multiple users
        colors = ['#FF69B4', '#1E90FF', '#32CD32', '#FFA500', '#9370DB', '#DC143C', '#00CED1']
        
        # Plot each person
        for i, person in enumerate(analysis_results):
            name = person['name']
            mbti = person['mbti']
            scores = align_scores_with_mbti(mbti, person['scores'])
            color = colors[i % len(colors)]
            
            # Stagger text position slightly to avoid overlap
            text_pos = "top center" if i % 2 == 0 else "bottom center"
            
            fig.add_trace(go.Scatter(
                x=scores, 
                y=[0,1,2,3], 
                mode='markers+text', 
                name=f'{name} ({mbti})', 
                marker=dict(size=20, color=color, line=dict(width=2, color='white')), 
                text=[str(v) for v in scores], 
                textposition=text_pos, 
                textfont=dict(color=color, weight='bold')
            ))
        
        fig.update_layout(
            title=dict(text=f"📊 Personality Spectrum Analysis", font=dict(size=20)), 
            height=500, 
            showlegend=True, 
            legend=dict(orientation="h", y=1.1, x=0.5, xanchor='center'), 
            xaxis=dict(range=[-25, 125], showgrid=False, zeroline=False, showticklabels=False), 
            yaxis=dict(range=[-0.5, 3.5], showgrid=False, zeroline=False, showticklabels=False), 
            plot_bgcolor='white', 
            margin=dict(l=60, r=60, t=80, b=20)
        )
        st.session_state.agent_chart = fig
    except Exception as e:
        print(e)
        st.session_state.agent_chart = None

# ==========================================
# 4. API Call
# ==========================================
def call_ollama_api(messages, api_key):
    url = f"{API_BASE_URL}/api/chat"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "gemma3:4b", "messages": messages, "stream": False, "options": {"temperature": 0.7}}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        if response.status_code == 200: return response.json().get('message', {})
        else: raise Exception(f"Server Error {response.status_code}: {response.text}")
    except Exception as e: raise Exception(f"Connection Failed: {str(e)}")

# ==========================================
# 5. Phase 1: Dynamic Group Analysis
# ==========================================
def run_dynamic_analysis(selected_speakers_data, api_key):
    # Construct the input for the LLM
    conversation_sample = ""
    for name, text in selected_speakers_data.items():
        # Limit text per person to avoid token overflow
        conversation_sample += f"Speaker [{name}]: {text[:600]}\n\n"

    system_prompt = """
    You are an expert MBTI analyst.
    Task: Analyze the provided text samples for EACH speaker independently.
    
    For EACH speaker, determine:
    1. MBTI Type (e.g., INTJ, ENFP).
    2. Intensity Scores (0-100) for the 4 dimensions:
       - Energy (I <30 ... E >70)
       - Information (S <30 ... N >70)
       - Decisions (T <30 ... F >70)
       - Lifestyle (J <30 ... P >70)

    【Output Format (JSON ONLY)】
    output a JSON object containing a list called "results".
    {
        "results": [
            { "name": "Name1", "mbti": "XXXX", "scores": [10, 20, 30, 40] },
            { "name": "Name2", "mbti": "XXXX", "scores": [80, 90, 10, 50] }
        ]
    }
    """
    
    messages = [
        {"role": "system", "content": system_prompt}, 
        {"role": "user", "content": conversation_sample}
    ]
    
    try:
        ai_msg = call_ollama_api(messages, api_key)
        # Robust JSON extraction
        match = re.search(r'\{.*\}', ai_msg.get('content', ''), re.DOTALL)
        if match: 
            return json.loads(match.group(0))
        else: 
            return None 
    except: return None

# ==========================================
# 6. Phase 2: Chat Agent (Bilingual & Multi-user)
# ==========================================
def chat_response_generator(user_input, api_key):
    ctx = st.session_state.context_data
    results = ctx.get('analysis_results', [])
    names = [r['name'] for r in results]
    
    user_lang_chinese = is_chinese(user_input)
    
    system_prompt = f"""
    You are a professional relationship consultant.
    Participants: {", ".join(names)}
    Analysis Data: {json.dumps(results)}
    
    【Tool Selection Logic】
    Output ONLY JSON.
    
    1. If user asks for "chart", "graph", "visualize", "光譜", "圖表":
       TOOL_CALL: {{ "name": "tool_generate_bipolar_chart" }}
       
    2. If user asks for "compatibility", "match rate", "契合度" AND there are EXACTLY 2 people:
       TOOL_CALL: {{ "name": "tool_calculate_compatibility" }}
       
    3. If user asks for "compatibility" but there is 1 person or 3+ people:
       Do NOT call the tool. Instead, explain that compatibility scores are designed for pairs, but you can analyze the group dynamics in text.
       
    4. Otherwise (advice, analysis): 
       **Reply in the same language as the user's input (English or Traditional Chinese).**
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in st.session_state.messages:
        if msg["role"] in ["user", "assistant"]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_input})
    
    try:
        res = call_ollama_api(messages, api_key)
        content = res.get('content', '')
        
        # 🔧 Tool 1: Chart
        if "tool_generate_bipolar_chart" in content:
            tool_generate_bipolar_chart(results)
            if user_lang_chinese:
                return f"已為 {len(results)} 位成員生成圖表（見上方）。"
            else:
                return f"Chart generated for {len(results)} participants (see above)."

        # 🔧 Tool 2: Compatibility (Only valid for 2 people)
        elif "tool_calculate_compatibility" in content:
            if len(results) == 2:
                s1 = results[0]['scores']
                s2 = results[1]['scores']
                score = tool_calculate_compatibility(s1, s2)
                if user_lang_chinese:
                    return f"經計算，{results[0]['name']} 與 {results[1]['name']} 的契合度為：**{score} 分**。"
                else:
                    return f"Calculated match score between {results[0]['name']} and {results[1]['name']}: **{score}/100**."
            else:
                return "Compatibility scores are only available for pairs. Please select exactly two people."

        else:
            return content
            
    except Exception as e:
        return f"Error: {str(e)}"

# ==========================================
# 7. UI Setup (Definitions BEFORE Usage)
# ==========================================
st.set_page_config(page_title="AI MBTI Agent", layout="wide")
st.title("🤖 AI MBTI Analyst (Group & Individual)")

with st.sidebar:
    api_key = st.text_input("Enter API Key", type="password")
    if st.button("🗑️ Reset Session"):
        st.session_state.clear()
        st.rerun()

# --- DEFINE FILE UPLOADER HERE ---
uploaded_file = st.file_uploader("📂 Upload Line Chat (.txt)", type=['txt'])

# --- NOW SAFE TO USE uploaded_file ---
if uploaded_file and api_key:
    file_content = uploaded_file.getvalue().decode("utf-8")
    
    # 1. Parse Speakers
    if not st.session_state.parsed_speakers:
        stringio = StringIO(file_content)
        speakers_dict = parse_line_chat_dynamic(stringio.read())
        
        if speakers_dict and len(speakers_dict) > 0:
            st.session_state.parsed_speakers = speakers_dict
        else:
            st.error("Could not find valid speakers. Please check file format.")

    # 2. Select Speakers UI
    if st.session_state.parsed_speakers:
        speakers = list(st.session_state.parsed_speakers.keys())
        
        if not st.session_state.analysis_done:
            st.subheader("👥 Select Participants")
            
            # Default to ALL speakers to include "i"
            selected_names = st.multiselect(
                "Who do you want to analyze?", 
                speakers, 
                default=speakers 
            )
            
            if st.button("🚀 Start Analysis"):
                if not selected_names:
                    st.warning("Please select at least one person.")
                else:
                    with st.spinner(f"Analyzing {len(selected_names)} people..."):
                        selected_data = {name: st.session_state.parsed_speakers[name] for name in selected_names}
                        result_json = run_dynamic_analysis(selected_data, api_key)
                        
                        if result_json and "results" in result_json:
                            st.session_state.context_data = {
                                "analysis_results": result_json["results"],
                                "dialogue": file_content
                            }
                            st.session_state.analysis_done = True
                            
                            # === RESTORED WELCOME MESSAGE ===
                            count = len(result_json["results"])
                            
                            # Build the list of names and types
                            intro = f"### ✅ Analysis Complete ({count} People)\n"
                            for p in result_json["results"]:
                                intro += f"* **{p['name']}**: {p['mbti']}\n"
                            
                            intro += "\n**You can now ask:**\n"
                            intro += "1. 📊 **\"Visualize the group\"** (Chart)\n"
                            intro += "2. 🤝 **\"How is our compatibility?\"** (Pairs only)\n"
                            intro += "3. 💡 **\"How should we work together?\"** (Advice)"
                            
                            st.session_state.messages.append({"role": "assistant", "content": intro})
                            st.rerun()
                        else:
                            st.error("Analysis Failed. Please try again.")

    # 3. Chat Interface
    if st.session_state.analysis_done:
        if st.session_state.agent_chart:
            st.info("📊 Chart Generated")
            st.plotly_chart(st.session_state.agent_chart, use_container_width=True)

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ask about the group or individuals..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = chat_response_generator(prompt, api_key)
                    st.markdown(response)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            if "Chart generated" in response or "生成" in response:
                st.rerun()

elif not api_key: 
    st.warning("Please enter your API Key to proceed.")