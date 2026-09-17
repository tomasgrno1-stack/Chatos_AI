import streamlit as st
import os
import re
import json
import time
from datetime import datetime
import streamlit.components.v1 as components
from google import genai
from google.genai import types

st.set_page_config(
    page_title="Polaris AI — Guiding Intelligence",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    .stApp {
        background-color: #0b0f17;
        color: #f1f5f9;
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #080c14;
        border-right: 1px solid #1a2234;
    }
    .new-chat-btn button {
        background: linear-gradient(135deg, #06b6d4, #3b82f6) !important;
        color: #020617 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 10px !important;
    }
    [data-testid="stChatMessage"] {
        background-color: #0e1422;
        border: 1px solid #1a2336;
        border-radius: 16px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
    }
    .streamlit-expanderHeader {
        background: #090e18 !important;
        border: 1px solid #1e293b !important;
        border-radius: 10px !important;
        color: #38bdf8 !important;
    }
</style>
""", unsafe_allow_html=True)

SYSTEM_PROMPTS = {
    "nova": "You are Polaris AI, an exceptionally intelligent, refined, and versatile conversational assistant. Format with clean Markdown.",
    "thinker": "You are Polaris AI in Deep Reasoning Mode. Enclose your internal reasoning strictly inside opening <thought> and closing </thought> tags. Then provide your final response.",
    "architect": "You are Polaris AI in Architect Mode. When writing code, provide complete, working HTML/CSS/JS or SVG blocks labeled with language identifier.",
    "scholar": "You are Polaris AI in Scholar Mode. Provide deeply grounded, comprehensive explanations."
}

if "conversations" not in st.session_state:
    st.session_state.conversations = {}

if "active_conv_id" not in st.session_state:
    new_id = "conv_" + str(int(time.time()))
    st.session_state.conversations[new_id] = {
        "title": "Nová konverzácia",
        "created_at": datetime.now().strftime("%d.%m %H:%M"),
        "messages": [],
        "mode": "nova",
        "web_search": False,
        "artifact": None
    }
    st.session_state.active_conv_id = new_id

if "active_artifact" not in st.session_state:
    st.session_state.active_artifact = None

if "show_canvas" not in st.session_state:
    st.session_state.show_canvas = False

active_id = st.session_state.active_conv_id
if active_id not in st.session_state.conversations:
    st.session_state.conversations[active_id] = {
        "title": "Nová konverzácia",
        "created_at": datetime.now().strftime("%d.%m %H:%M"),
        "messages": [],
        "mode": "nova",
        "web_search": False,
        "artifact": None
    }

current_conv = st.session_state.conversations[active_id]
api_key = os.environ.get("GEMINI_API_KEY") or (st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else "")

with st.sidebar:
    st.markdown("### ✨ **POLARIS AI**")
    
    st.markdown("<div class='new-chat-btn'>", unsafe_allow_html=True)
    if st.button("➕ Nový chat", use_container_width=True):
        new_id = "conv_" + str(int(time.time()))
        st.session_state.conversations[new_id] = {
            "title": "Nová konverzácia",
            "created_at": datetime.now().strftime("%d.%m %H:%M"),
            "messages": [],
            "mode": current_conv.get("mode", "nova"),
            "web_search": current_conv.get("web_search", False),
            "artifact": None
        }
        st.session_state.active_conv_id = new_id
        st.session_state.active_artifact = None
        st.session_state.show_canvas = False
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # Výber modelu - Gemini 2.5 Flash je najodolnejší voči 429
    selected_model_name = st.selectbox(
        "Vyber Model:",
        ["gemini-2.5-flash", "gemini-3.8-flash"],
        index=0
    )

    mode_options = {
        "nova": "⚡ Polaris Nova (Rýchly)",
        "thinker": "🧠 Polaris Thinker (Uvažovanie)",
        "architect": "🛠️ Polaris Architect (Canvas & Kód)",
        "scholar": "📚 Polaris Scholar (Výskum)"
    }
    selected_mode_key = st.selectbox("Režim:", list(mode_options.keys()), format_func=lambda k: mode_options[k])
    current_conv["mode"] = selected_mode_key

    web_search = st.toggle("🌐 Web Search Grounding", value=current_conv.get("web_search", False))
    current_conv["web_search"] = web_search

    uploaded_file = st.file_uploader("📎 Priložiť súbor / obrázok:", type=["png", "jpg", "jpeg", "txt", "py", "html", "md"])

    st.markdown("---")
    for cid, c in list(st.session_state.conversations.items())[::-1]:
        is_active = (cid == active_id)
        c1, c2 = st.columns([8, 2])
        with c1:
            if st.button(f"{'✨ ' if is_active else '💬 '}{c['title'][:20]}", key=f"btn_{cid}", use_container_width=True):
                st.session_state.active_conv_id = cid
                st.session_state.active_artifact = c.get("artifact")
                st.rerun()
        with c2:
            if st.button("🗑️", key=f"del_{cid}"):
                del st.session_state.conversations[cid]
                st.rerun()

    if not api_key:
        api_key_input = st.text_input("🔑 Zadaj Gemini API kľúč:", type="password")
        if api_key_input:
            api_key = api_key_input
            os.environ["GEMINI_API_KEY"] = api_key
            st.rerun()
    else:
        with st.expander("🔑 Zmeniť API Kľúč"):
            new_k = st.text_input("Nový kľúč:", type="password")
            if st.button("Uložiť") and new_k:
                os.environ["GEMINI_API_KEY"] = new_k
                st.rerun()

def extract_artifact(text: str):
    html_match = re.search(r"```(?:html|htm)\s*([\s\S]*?)```", text, re.IGNORECASE)
    if html_match:
        return {"type": "html", "code": html_match.group(1).strip(), "title": "Web Canvas"}
    svg_match = re.search(r"```(?:svg)\s*([\s\S]*?)```", text, re.IGNORECASE) or re.search(r"(<svg[\s\S]*?<\/svg>)", text, re.IGNORECASE)
    if svg_match:
        return {"type": "svg", "code": svg_match.group(1).strip(), "title": "SVG Canvas"}
    return None

show_split = st.session_state.show_canvas and st.session_state.active_artifact is not None
chat_col, canvas_col = st.columns([6, 5]) if show_split else (st.container(), None)

with chat_col:
    messages = current_conv.get("messages", [])
    
    for idx, msg in enumerate(messages):
        with st.chat_message(msg["role"], avatar="✨" if msg["role"] == "assistant" else None):
            if msg.get("image_bytes"):
                st.image(msg["image_bytes"], width=250)
            content = msg["content"]
            thought_match = re.search(r"<thought>([\s\S]*?)</thought>", content)
            if thought_match:
                with st.expander("🧠 Proces uvažovania (Thinking Process)", expanded=False):
                    st.code(thought_match.group(1).strip())
                st.markdown(re.sub(r"<thought>[\s\S]*?</thought>", "", content).strip())
            else:
                st.markdown(content)
            
            art = extract_artifact(content)
            if art and msg["role"] == "assistant":
                if st.button("🚀 Spustiť v Canvase", key=f"btn_art_{idx}"):
                    st.session_state.active_artifact = art
                    st.session_state.show_canvas = True
                    st.rerun()

if show_split and canvas_col:
    with canvas_col:
        artifact = st.session_state.active_artifact
        st.markdown(f"**🖥️ Polaris Canvas** ({artifact['title']})")
        t_prev, t_code = st.tabs(["▶️ Náhľad", "💻 Kód"])
        with t_prev:
            code = artifact["code"]
            html_to_run = f"<!DOCTYPE html><html><head><script src='https://cdn.tailwindcss.com'></script></head><body style='background:#0c0f17;color:white;padding:15px;'>{code}</body></html>" if "<html" not in code else code
            components.html(html_to_run, height=540, scrolling=True)
        with t_code:
            st.code(artifact["code"])

prompt = st.chat_input("Opýtaj sa Polaris čokoľvek...")
if prompt:
    if not api_key:
        st.error("Chýba Gemini API kľúč!")
        st.stop()
        
    img_bytes = None
    if uploaded_file and uploaded_file.type.startswith("image/"):
        img_bytes = uploaded_file.getvalue()
        
    messages.append({"role": "user", "content": prompt, "image_bytes": img_bytes})
    if len(messages) == 1:
        current_conv["title"] = prompt[:24]

    with chat_col:
        with st.chat_message("user"):
            if img_bytes:
                st.image(img_bytes, width=250)
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="✨"):
            msg_placeholder = st.empty()
            full_text = ""
            client = genai.Client(api_key=api_key)
            
            api_contents = []
            for m in messages:
                parts = []
                if m.get("image_bytes"):
                    parts.append(types.Part.from_bytes(data=m["image_bytes"], mime_type="image/png"))
                if m.get("content"):
                    parts.append(types.Part.from_text(text=m["content"]))
                api_contents.append(types.Content(role="model" if m["role"] == "assistant" else "user", parts=parts))

            # Skúšanie primárneho a záložného modelu v prípade 429
            models_to_try = [selected_model_name, "gemini-2.5-flash", "gemini-2.0-flash"]
            success = False

            for m_name in models_to_try:
                try:
                    stream = client.models.generate_content_stream(
                        model=m_name,
                        contents=api_contents,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPTS[current_conv.get("mode", "nova")],
                            tools=[{"google_search": {}}] if current_conv.get("web_search") else None
                        )
                    )
                    for chunk in stream:
                        if chunk.text:
                            full_text += chunk.text
                            msg_placeholder.markdown(full_text + " ▌")
                    success = True
                    break
                except Exception as ex:
                    if "429" in str(ex) or "RESOURCE_EXHAUSTED" in str(ex):
                        msg_placeholder.info(f"Kvóta pre {m_name} vyčerpaná. Pripájam záložný model...")
                        time.sleep(1)
                        full_text = ""
                        continue
                    else:
                        st.error(f"Chyba: {ex}")
                        break

            if success:
                msg_placeholder.markdown(full_text)
                new_art = extract_artifact(full_text)
                if new_art:
                    st.session_state.active_artifact = new_art
                    st.session_state.show_canvas = True
                    st.rerun()
                messages.append({"role": "assistant", "content": full_text})
            else:
                st.error("⏳ Kvóta bezplatného Gemini API je prečerpaná. Počkaj 1 minútu alebo vytvor nový kľúč na https://aistudio.google.com/app/apikey.")
