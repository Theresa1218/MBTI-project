import requests
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL", "https://api-gateway.netdb.csie.ncku.edu.tw")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.1")

# ===========================
# 1. Tool Definitions
# ===========================
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "calculate_compatibility",
            "description": "Calculate compatibility score between two people",
            "parameters": {
                "type": "object",
                "properties": {
                    "scores_a": {"type": "array", "items": {"type": "integer"}},
                    "scores_b": {"type": "array", "items": {"type": "integer"}}
                },
                "required": ["scores_a", "scores_b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_chart_display",
            "description": "顯示圖表",
            "parameters": {
                "type": "object",
                "properties": {"action": {"type": "string", "enum": ["show"]}},
                "required": ["action"]
            }
        }
    }
]

# ===========================
# 2. 實作邏輯
# ===========================
def calculate_compatibility(scores_a, scores_b):
    try:
        diff = sum(abs(a - b) for a, b in zip(scores_a, scores_b))
        score = max(10, 100 - int(diff * 0.25))
        return json.dumps({"score": score})
    except:
        return json.dumps({"score": 50})

def parse_line_chat(file_content):
    lines = file_content.split('\n')
    messages = {}
    pattern = re.compile(r'^\d{1,2}:\d{2}\t?([^\t]+)\t?(.+)')
    for line in lines:
        match = pattern.match(line.strip())
        if match:
            name, msg = match.group(1).strip(), match.group(2).strip()
            if any(x in msg for x in ["通話", "貼圖", "照片"]): continue
            if name not in messages: messages[name] = []
            messages[name].append(msg)
    
    sorted_speakers = sorted(messages, key=lambda k: len(messages[k]), reverse=True)
    if len(sorted_speakers) < 2: return None
    p1, p2 = sorted_speakers[0], sorted_speakers[1]
    
    return {"p1": p1, "text_a": "\n".join(messages[p1])[:800], "p2": p2, "text_b": "\n".join(messages[p2])[:800]}

def call_llm(messages, use_tools=False):
    url = f"{API_URL}/api/chat"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.5,
            "num_ctx": 4096 
        }
    }
    if use_tools: payload["tools"] = TOOLS_SCHEMA

    print(f"📡 呼叫 AI 中... (Model: {MODEL_NAME})") 

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=300)
        
        if res.status_code == 200: 
            return res.json().get('message', {})
        else:
            print(f"❌ Server Error: {res.status_code} - {res.text}")
            return None
    except Exception as e:
        print(f"❌ Connection Timeout or Error: {e}")
        return None

def analyze_mbti_initial(data):
    prompt = f"""Analyze chat. Output JSON ONLY: {{"mbti_a": "ESTJ", "scores_a": [80,20,80,80], "mbti_b": "INFP", "scores_b": [20,80,20,20]}}\nA: {data['text_a']}\nB: {data['text_b']}"""
    res = call_llm([{"role": "user", "content": prompt}])
    try:
        content = res['content']
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match: return json.loads(match.group(0))
    except: pass
    return {"mbti_a": "ESTP", "scores_a": [60,40,60,40], "mbti_b": "INFJ", "scores_b": [40,60,40,60]}

def agent_chat_loop(user_input, context, history):
    system_msg = {"role": "system", "content": f"Context: {context}. Query scores? call calculate_compatibility. Query chart? call trigger_chart_display."}
    messages = [system_msg] + history + [{"role": "user", "content": user_input}]
    
    ai_msg = call_llm(messages, use_tools=True)
    if not ai_msg: return "⚠️ API 連線逾時或錯誤，請檢查終端機訊息。", False
    
    show_chart = False
    if "tool_calls" in ai_msg and ai_msg["tool_calls"]:
        tool = ai_msg["tool_calls"][0]
        fname = tool["function"]["name"]
        
        tool_res = ""
        if fname == "calculate_compatibility":
            tool_res = calculate_compatibility(context['scores_a'], context['scores_b'])
        elif fname == "trigger_chart_display":
            tool_res = json.dumps({"status": "ok"})
            show_chart = True
            
        messages.append(ai_msg)
        messages.append({"role": "tool", "content": tool_res})
        final_res = call_llm(messages, use_tools=False)
        return final_res['content'], show_chart
        
    return ai_msg['content'], False