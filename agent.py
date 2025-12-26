import os
import json
import re  # <--- This is the key tool to fix the error
import requests
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 1. API Caller
# ==========================================
def call_ollama_api(messages, api_key, base_url, model_name):
    # Ensure URL is correct
    base_url = base_url.rstrip('/')
    url = f"{base_url}/api/chat"
    
    headers = {"Content-Type": "application/json"}
    if api_key and api_key != "ollama":
        headers["Authorization"] = f"Bearer {api_key}"
    
    # FORCE JSON MODE
    payload = {
        "model": model_name, 
        "messages": messages, 
        "stream": False, 
        "format": "json", # Forces the model to be stricter
        "options": {"temperature": 0.7}
    }
    
    try:
        # Increase timeout to 180s to prevent "Read timed out"
        response = requests.post(url, json=payload, headers=headers, timeout=180)
        
        if response.status_code == 200: 
            return response.json().get('message', {})
        elif response.status_code == 404:
            raise Exception(f"Model '{model_name}' not found. Try running 'ollama pull {model_name}'")
        else: 
            raise Exception(f"Error {response.status_code}: {response.text}")
            
    except requests.exceptions.ConnectionError:
        raise Exception("Could not connect to Ollama. Is the app running?")
    except Exception as e: 
        raise Exception(f"Connection Failed: {str(e)}")


# ==========================================
# 2. Analysis Function (With "Extra Data" Fix)
# ==========================================
def run_analysis_request(system_prompt, user_content, api_key, base_url, model_name):
    messages = [
        {"role": "system", "content": system_prompt}, 
        {"role": "user", "content": user_content}
    ]
    try:
        ai_msg = call_ollama_api(messages, api_key, base_url, model_name)
        content = ai_msg.get('content', '')
        
        # --- THE FIX IS HERE ---
        # 1. Try to find the JSON hidden inside the text
        # This regex looks for the content between the first '{' and the last '}'
        match = re.search(r'\{.*\}', content, re.DOTALL)
        
        if match:
            clean_json = match.group(0) # This is just the {...} part
            return json.loads(clean_json)
        
        # 2. Fallback: Try to parse the whole thing if regex failed
        return json.loads(content)

    except Exception as e: 
        # Show the raw content to help debug if it fails again
        return {"error": f"JSON Parse Error: {str(e)}"}


# ==========================================
# 3. Chat Function
# ==========================================
def generate_chat_response(user_input, chat_history, context_results, api_key, base_url, model_name, is_chinese_func):
    names = [r['name'] for r in context_results]
    
    system_prompt = f"""
    You are a relationship consultant.
    Participants: {", ".join(names)}
    Data: {json.dumps(context_results)}
    
    IMPORTANT: If the user asks for a visualization, chart, or graph, output EXACTLY this JSON:
    {{ "name": "tool_generate_bipolar_chart" }}
    
    Otherwise, answer their question naturally.
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add history
    for msg in chat_history:
        if msg["role"] in ["user", "assistant"]:
            # Skip tool messages to avoid confusing the model
            if "📊" not in msg["content"]: 
                messages.append({"role": msg["role"], "content": msg["content"]})
            
    messages.append({"role": "user", "content": user_input})
    
    try:
        # Note: We do NOT use "format": "json" here because normal chat needs text
        base_url = base_url.rstrip('/')
        url = f"{base_url}/api/chat"
        headers = {"Content-Type": "application/json"}
        if api_key and api_key != "ollama": headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model_name, 
            "messages": messages, 
            "stream": False,
            "options": {"temperature": 0.7}
        }

        response = requests.post(url, json=payload, headers=headers, timeout=120)
        content = response.json()['message']['content']
        
        # Check if the AI wants to make a chart
        if "tool_generate_bipolar_chart" in content:
            return "TOOL:CHART", None
        
        return content, None
            
    except Exception as e:
        return f"Error: {str(e)}", None