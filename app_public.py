import streamlit as st
import os
import re
from google import genai
from google.genai import types

st.set_page_config(
    page_title="Polaris AI",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Dark Theme & ChatGPT-like styling
st.markdown("""
<style>
    .stApp {
        background-color: #0c0f17;
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #090d16;
        border-right: 1px solid #1e293b;
    }
    [data-testid="stChatMessage"] {
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.75rem;
    }
    .streamlit-expanderHeader {
        background-color: #111726 !important;
        border-radius: 8px !important;
        color: #38bdf8 !important;
    }
</style>
""", unsafe_allow_html=True)

SYSTEM_PROMPTS = {
    "Polaris Nova (Rýchly & Univerzálny)": (
        "You are Polaris AI, an exceptionally intelligent, refined, and versatile conversational intelligence. "
        "Provide crisp, direct, and insightful answers with clean Markdown and code formatting."
    ),
    "Polaris Thinker (Hĺbkové Uvažovanie)": (
        "You are Polaris AI in Deep Reasoning mode. "
        "For complex questions, first think step-by-step. "
        "Place your internal reasoning inside <thought> and </thought> tags. "
        "Then provide your final answer."
    ),
    "Polaris Architect (Programovanie & Kód)": (
        "You are Polaris AI in Architect mode. "
        "Provide production-grade, maintainable code blocks with language identifiers."
    ),
    "Polaris Scholar (Výskum & Veda)": (
        "You are Polaris AI in Scholar mode. Provide rigorous, citation-backed scientific explanations."
    )
}

api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")

with st.sidebar:
    st.markdown("### ✨ **POLARIS AI**")
    st.caption("Guiding Intelligence · Powered by Gemini 3.8")
    
    if not api_key:
        api_key_input = st.text_input("Zadaj Gemini API kľúč:", type="password")
        if api_key_input:
            api_key = api_key_input
            os.environ["GEMINI_API_KEY"] = api_key
    
    st.markdown("---")
    selected_mode = st.selectbox("🧠 Režim Inteligencie:", list(SYSTEM_PROMPTS.keys()), index=0)
    web_search = st.toggle("🌐 Google Search Grounding", value=False)
    
    st.markdown("---")
    if st.button("🗑️ Vymazať konverzáciu", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

st.markdown("## ✨ **Polaris AI**")

# Zobrazenie histórie správ
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="✨" if msg["role"] == "assistant" else None):
        thought_match = re.search(r"<thought>([\s\S]*?)</thought>", msg["content"])
        if thought_match:
            thought_text = thought_match.group(1).strip()
            clean_content = re.sub(r"<thought>[\s\S]*?</thought>", "", msg["content"]).strip()
            with st.expander("🧠 Proces uvažovania (Thinking Process)", expanded=False):
                st.code(thought_text)
            st.markdown(clean_content)
        else:
            st.markdown(msg["content"])

prompt = st.chat_input("Opýtaj sa Polaris čokoľvek...")

if prompt:
    if not api_key:
        st.error("Chýba Gemini API kľúč! Zadaj ho v bočnom paneli alebo v nastaveniach Streamlit Secrets.")
        st.stop()
        
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="✨"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            client = genai.Client(api_key=api_key)
            
            contents = [
                types.Content(
                    role="model" if m["role"] == "assistant" else "user",
                    parts=[types.Part.from_text(text=m["content"])]
                ) for m in st.session_state.messages
            ]
            
            tools = [{"google_search": {}}] if web_search else None
            
            stream = client.models.generate_content_stream(
                model="gemini-3.8-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPTS[selected_mode],
                    tools=tools
                )
            )
            
            for chunk in stream:
                if chunk.text:
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + " ▌")
            
            thought_match = re.search(r"<thought>([\s\S]*?)</thought>", full_response)
            if thought_match:
                thought_text = thought_match.group(1).strip()
                clean_content = re.sub(r"<thought>[\s\S]*?</thought>", "", full_response).strip()
                message_placeholder.empty()
                with st.expander("🧠 Proces uvažovania (Thinking Process)", expanded=False):
                    st.code(thought_text)
                st.markdown(clean_content)
            else:
                message_placeholder.markdown(full_response)
                
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Chyba pri generovaní odpovede: {e}")
