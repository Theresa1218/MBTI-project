import streamlit as st
from agent import parse_line_chat, analyze_mbti_initial, agent_chat_loop
from charts import draw_bipolar_chart

st.set_page_config(page_title="AI MBTI Agent", layout="wide")

# ========================
# 1. Initial Session State 
# ========================
if "ctx" not in st.session_state: st.session_state.ctx = {}
if "messages" not in st.session_state: st.session_state.messages = []
if "show_chart" not in st.session_state: st.session_state.show_chart = False

st.title("🤖 MBTI Analysis Agent")

# ========================
# 2. Sidebar - File Upload
# ========================
with st.sidebar:
    st.header("File Upload")
    uploaded_file = st.file_uploader("Upload Line Chat (.txt)", type=['txt'])

# ========================
# 3. Main Logic
# ========================

# Phase 1: Analysis
if uploaded_file and not st.session_state.ctx:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    parsed = parse_line_chat(raw_text)
    
    if parsed:
        st.info("已讀取檔案，準備進行分析...")
        if st.button("🚀 Start MBTI Analysis"):
            with st.spinner("AI Analyzing..."):
                # Call MBTI Analysis
                analysis = analyze_mbti_initial(parsed)
                # Write into Session State
                st.session_state.ctx = {
                    "p1": parsed['p1'], "p2": parsed['p2'],
                    **analysis
                }
                st.rerun()
    else:
        st.error("無法解析檔案，請確認格式 (需包含時間與人名)。")

# Phase 2: Interact and Charts
if st.session_state.ctx:
    ctx = st.session_state.ctx
    
    # 資訊看板
    col1, col2 = st.columns(2)
    col1.info(f"👤 {ctx['p1']}: {ctx.get('mbti_a')} (Scores: {ctx.get('scores_a')})")
    col2.info(f"👤 {ctx['p2']}: {ctx.get('mbti_b')} (Scores: {ctx.get('scores_b')})")

    # 動態顯示圖表
    if st.session_state.show_chart:
        st.subheader("📊 性格光譜分析")
        try:
            fig = draw_bipolar_chart(
                ctx['mbti_a'], ctx['mbti_b'], 
                ctx['p1'], ctx['p2'], 
                ctx['scores_a'], ctx['scores_b']
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"圖表生成錯誤: {e}")

    # 聊天室區域
    st.divider()
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 輸入框
    if prompt := st.chat_input("Question about the MBTI analysis?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Agent thinking..."):
                # Call Agent Loop
                reply, trigger_chart = agent_chat_loop(
                    prompt, st.session_state.ctx, st.session_state.messages
                )
                
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

                # If the agent wants to show the chart
                if trigger_chart:
                    st.session_state.show_chart = True
                    st.rerun()