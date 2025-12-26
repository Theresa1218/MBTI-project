import re
import json

# ==========================================
# 1. Language Helper
# ==========================================
def is_chinese(text):
    """Check if input text contains Chinese characters."""
    return bool(re.search(r'[\u4e00-\u9fff]', text))

# ==========================================
# 2. Scoring Helper
# ==========================================
def align_scores_with_mbti(mbti_type, raw_scores):
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

# ==========================================
# 3. File Parser
# ==========================================
def parse_line_chat_dynamic(file_content):
    lines = file_content.split('\n')
    messages = {}
    
    skip_keywords = ["通話時間", "Call time", "Unsend message", "joined the chat", "invite"]
    invalid_names = ["You", "you", "System", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    for line in lines:
        line = line.strip()
        if not line: continue
        parts = line.split('\t')
        if len(parts) < 3: parts = line.split(' ', 2)

        if len(parts) >= 3:
            time_str, name, msg = parts[0], parts[1].strip(), parts[2].strip()
            
            if not re.match(r'^\d{1,2}:\d{2}$', time_str): continue
            if name.endswith(" Photos") or name.endswith(" Stickers"): name = name.replace(" Photos", "").replace(" Stickers", "")
            if any(k in msg for k in skip_keywords): continue
            if msg in ["[Photos]", "[Stickers]"]: continue 
            if name in invalid_names: continue

            if name not in messages: messages[name] = []
            messages[name].append(msg)
            
    return {k: "\n".join(v) for k, v in messages.items() if len(v) >= 3}

# ==========================================
# 4. Prompt Constructor
# ==========================================
def construct_analysis_prompt(selected_speakers_data):
    conversation_sample = ""
    for name, text in selected_speakers_data.items():
        conversation_sample += f"Speaker [{name}]: {text[:600]}\n\n"

    system_prompt = """
    You are an expert MBTI analyst.
    Task: Analyze the provided text samples for EACH speaker independently.
    Output JSON ONLY:
    { "results": [ { "name": "Name1", "mbti": "XXXX", "scores": [10, 20, 30, 40] } ] }
    """
    return system_prompt, conversation_sample