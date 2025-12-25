import streamlit as st
import json
import re
import plotly.graph_objects as go
from io import StringIO
import requests

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

# ==========================================
# 2. Logic Correction Helper
# ==========================================
def align_scores_with_mbti(mbti_type, raw_scores):
    if not mbti_type or len(raw_scores) != 4:
        return [50, 50, 50, 50]
    mbti = mbti_type.upper()
    corrected = list(raw_scores)
    # E/I
    if 'I' in mbti: corrected[0] = min(corrected[0], 45)
    elif 'E' in mbti: corrected[0] = max(corrected[0], 55)
    # S/N
    if 'S' in mbti: corrected[1] = min(corrected[1], 45)
    elif 'N' in mbti: corrected[1] = max(corrected[1], 55)
    # T/F
    if 'T' in mbti: corrected[2] = min(corrected[2], 45)
    elif 'F' in mbti: corrected[2] = max(corrected[2], 55)
    # J/P
    if 'J' in mbti: corrected[3] = min(corrected[3], 45)
    elif 'P' in mbti: corrected[3] = max(corrected[3], 55)
    return corrected

# ==========================================
# 3. Tools Definition 
# ==========================================
def parse_line_chat(file_content):
    lines = file_content.split('\n')
    messages = {}
    pattern = re.compile(r'^\d{1,2}:\d{2}\t?([^\t]+)\t?(.+)')
    for line in lines:
        match = pattern.match(line.strip())
        if match:
            name = match.group(1).strip()
            msg = match.group(2).strip()
            if "通話時間" in msg or "[貼圖]" in msg or "[照片]" in msg: continue
            if name not in messages: messages[name] = []
            messages[name].append(msg)
    sorted_speakers = sorted(messages, key=lambda k: len(messages[k]), reverse=True)
    if len(sorted_speakers) < 2: return None
    p1, p2 = sorted_speakers[0], sorted_speakers[1]
    return p1, "\n".join(messages[p1]), p2, "\n".join(messages[p2])

# 🛠️ Tool 1: Compatibility Calculator
def tool_calculate_compatibility(scores_a, scores_b):
    try:
        diff_sum = 0
        for a, b in zip(scores_a, scores_b):
            diff_sum += abs(a - b)
        
        # 滿分 100，每差 1 分扣 0.25
        score = 100 - (diff_sum * 0.25)
        return max(10, min(99, int(score))) # limit: 10-99 
    except:
        return 50

# 🛠️ Tool 2: Bipolar Chart Generator
def tool_generate_bipolar_chart(mbti_a, mbti_b, name_a, name_b, scores_a, scores_b):
    try:
        final_a = align_scores_with_mbti(mbti_a, scores_a)
        final_b = align_scores_with_mbti(mbti_b, scores_b)
        dimensions = [
            {"label": "Energy (能量方向)", "left": "I (Introversion)", "right": "E (Extraversion)", "y": 0},
            {"label": "Information (資訊獲取)", "left": "S (Sensing)", "right": "N (Intuition)", "y": 1},
            {"label": "Decisions (決策依據)", "left": "T (Thinking)", "right": "F (Feeling)", "y": 2},
            {"label": "Lifestyle (生活方式)", "left": "J (Judging)", "right": "P (Perceiving)", "y": 3}
        ]
        fig = go.Figure()
        for dim in dimensions:
            fig.add_shape(type="line", x0=0, y0=dim['y'], x1=100, y1=dim['y'], line=dict(color="#E0E0E0", width=6))
            fig.add_annotation(x=-8, y=dim['y'], text=dim['left'], showarrow=False, xanchor="right", font=dict(size=14, color="#555"))
            fig.add_annotation(x=108, y=dim['y'], text=dim['right'], showarrow=False, xanchor="left", font=dict(size=14, color="#555"))
        
        fig.add_trace(go.Scatter(x=final_a, y=[0,1,2,3], mode='markers+text', name=f'{name_a} ({mbti_a})', marker=dict(size=22, color='#FF69B4', line=dict(width=2, color='white')), text=[str(v) for v in final_a], textposition="top center", textfont=dict(color='#FF69B4', weight='bold')))
        fig.add_trace(go.Scatter(x=final_b, y=[0,1,2,3], mode='markers+text', name=f'{name_b} ({mbti_b})', marker=dict(size=22, color='#1E90FF', line=dict(width=2, color='white')), text=[str(v) for v in final_b], textposition="bottom center", textfont=dict(color='#1E90FF', weight='bold')))
        
        fig.update_layout(title=dict(text=f"📊 {name_a} vs {name_b} Personality Spectrum", font=dict(size=20)), height=450, showlegend=True, legend=dict(orientation="h", y=1.1, x=0.5, xanchor='center'), xaxis=dict(range=[-25, 125], showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(range=[-0.5, 3.5], showgrid=False, zeroline=False, showticklabels=False), plot_bgcolor='white', margin=dict(l=50, r=50, t=80, b=20))
        st.session_state.agent_chart = fig
    except: st.session_state.agent_chart = None

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
# 5. Phase 1: Analysis
# ==========================================
def run_initial_analysis(p1_name, text_a, p2_name, text_b, api_key):
    system_prompt = f"""
    You are an expert MBTI analyst.
    Task: Analyze the conversation intensity between {p1_name} and {p2_name}.
    
    1. Determine MBTI types based on keywords and tone.
    2. **Calculate Intensity Scores (0-100) based on UNIVERSAL behavioral patterns:**
    
       - **Energy (I vs E):**
         - Score < 30 (Introvert): Reflective, concise, internal processing, passive responder.
         - Score > 70 (Extrovert): Expressive, initiating, external processing, active contributor.
       
       - **Information (S vs N):**
         - Score < 30 (Sensing): **Concrete & Practical**. Focuses on details, current reality, "what is", step-by-step.
         - Score > 70 (Intuition): **Abstract & Conceptual**. Focuses on patterns, future possibilities, "what could be", metaphors.
       
       - **Decisions (T vs F):**
         - Score < 30 (Thinking): **Objective**. Focuses on logic, critique, cause-and-effect, truth over tact.
         - Score > 70 (Feeling): **Subjective**. Focuses on personal values, harmony, empathy, impact on people.
       
       - **Lifestyle (J vs P):**
         - Score < 30 (Judging): **Structured**. Prefers closure, planning, control, deciding things.
         - Score > 70 (Prospecting): **Flexible**. Prefers options, adapting, spontaneity, exploring things.
    【Output Format (JSON ONLY)】
    {{
        "mbti_person_a": "XXXX", "scores_a": [E, N, F, P],
        "mbti_person_b": "XXXX", "scores_b": [E, N, F, P]
    }}
    """
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"A: {text_a[:1000]}\nB: {text_b[:1000]}"}]
    try:
        ai_msg = call_ollama_api(messages, api_key)
        match = re.search(r'\{.*\}', ai_msg.get('content', ''), re.DOTALL)
        if match: return json.loads(match.group(0))
        else: return None 
    except: return None

# ==========================================
# 6. Phase 2: Chat Agent 
# ==========================================
def chat_response_generator(user_input, api_key):
    ctx = st.session_state.context_data
    
    system_prompt = f"""
    You are a professional relationship consultant.
    Case: {ctx.get('p1')} ({ctx.get('mbti_a')}) vs {ctx.get('p2')} ({ctx.get('mbti_b')})
    Context: {ctx.get('dialogue', '')[:1000]}
    
    【Tool Selection Logic】
    You must decide which tool to use based on user input. Output ONLY the JSON.
    
    1. If user asks for "chart", "graph", "visualize":
       TOOL_CALL: {{ "name": "tool_generate_bipolar_chart" }}
       
    2. If user asks for "compatibility score", "match rate", "how compatible are we":
       TOOL_CALL: {{ "name": "tool_calculate_compatibility" }}
       
    3. Otherwise (advice, analysis): Reply in Traditional Chinese directly.
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in st.session_state.messages:
        if msg["role"] in ["user", "assistant"]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_input})
    
    try:
        res = call_ollama_api(messages, api_key)
        content = res.get('content', '')
        
        # 🔧 判斷工具 1：畫圖
        if "tool_generate_bipolar_chart" in content:
            tool_generate_bipolar_chart(
                ctx.get('mbti_a'), ctx.get('mbti_b'),
                ctx.get('p1'), ctx.get('p2'),
                ctx.get('scores_a'), ctx.get('scores_b')
            )
            return "圖表已生成（請見上方）！這張圖能讓您看清雙方的差異。"

        # 🔧 判斷工具 2：算分 
        elif "tool_calculate_compatibility" in content:
            score = tool_calculate_compatibility(ctx.get('scores_a'), ctx.get('scores_b'))
            return f"經過綜合計算，兩位的性格契合度指數為：**{score} 分**。\n\n)"

        else:
            return content
            
    except Exception as e:
        return f"Connection error ({str(e)})"

# ==========================================
# 7. UI
# ==========================================
st.set_page_config(page_title="AI Agent MBTI", layout="wide")
st.title("🤖 MBTI Relationship Agent")

with st.sidebar:
    api_key = st.text_input("Enter API Key", type="password")
    if st.button("🗑️ End Session"):
        st.session_state.clear()
        st.rerun()

uploaded_file = st.file_uploader("📂 Upload (.txt)", type=['txt'])

if uploaded_file and api_key:
    file_content = uploaded_file.getvalue().decode("utf-8")
    
    if not st.session_state.analysis_done:
        stringio = StringIO(file_content)
        parse_res = parse_line_chat(stringio.read())
        
        if parse_res:
            p1, t1, p2, t2 = parse_res
            if st.button("🚀 Start Analysis"):
                with st.spinner("Analyzing..."):
                    result = run_initial_analysis(p1, t1, p2, t2, api_key)
                    if result:
                        st.session_state.context_data = {
                            "p1": p1, "p2": p2,
                            "mbti_a": result.get('mbti_person_a', 'N/A'),
                            "mbti_b": result.get('mbti_person_b', 'N/A'),
                            "scores_a": result.get('scores_a', [50,50,50,50]),
                            "scores_b": result.get('scores_b', [50,50,50,50]),
                            "dialogue": file_content
                        }
                        st.session_state.analysis_done = True
                        welcome = f"Analysis Complete.\n**{p1}** ({st.session_state.context_data['mbti_a']}) vs **{p2}** ({st.session_state.context_data['mbti_b']}).\n\n您可以問我：\n1. **「幫我畫圖」** (看光譜)\n2. **「我們契合度幾分？」** (算分數)\n3. **「怎麼解決爭吵？」** (求建議)"
                        st.session_state.messages.append({"role": "assistant", "content": welcome})
                        st.rerun()
                    else: st.error("Analysis Failed")
        else: st.error("Invalid File")

    else:
        if st.session_state.agent_chart:
            st.info("📊 Chart Generated")
            st.plotly_chart(st.session_state.agent_chart, use_container_width=True)

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ask something..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = chat_response_generator(prompt, api_key)
                    st.markdown(response)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            if "圖表" in response or "生成" in response:
                st.rerun()

elif not api_key:
    st.warning("Please enter API Key")