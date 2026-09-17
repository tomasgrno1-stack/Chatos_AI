import streamlit as st
import os
import re
import json
import time
from datetime import datetime
import streamlit.components.v1 as components
from google import genai
from google.genai import types

# -----------------------------------------------------------------------------
# 1. Nastavenie stránky Streamlit
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Polaris AI — Guiding Intelligence",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. Vlastný Tmavý Obsidian Dizajn (ChatGPT štýl s vylepšeniami)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Hlavné pozadie a písmo */
    .stApp {
        background-color: #0b0f17;
        color: #f1f5f9;
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    }

    /* Bočný panel */
    [data-testid="stSidebar"] {
        background-color: #080c14;
        border-right: 1px solid #1a2234;
    }
    
    [data-testid="stSidebar"] .stButton>button {
        background: #131a2a;
        color: #e2e8f0;
        border: 1px solid #1e293b;
        border-radius: 10px;
        font-weight: 500;
        font-size: 0.85rem;
        transition: all 0.2s ease;
        text-align: left;
    }
    [data-testid="stSidebar"] .stButton>button:hover {
        background: #1e293b;
        border-color: #38bdf8;
        color: #38bdf8;
        transform: translateY(-1px);
    }

    /* Tlačidlo Nový Chat */
    .new-chat-btn button {
        background: linear-gradient(135deg, #06b6d4, #3b82f6) !important;
        color: #020617 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 14px rgba(6, 182, 212, 0.25) !important;
    }

    /* Správy v chate */
    [data-testid="stChatMessage"] {
        background-color: #0e1422;
        border: 1px solid #1a2336;
        border-radius: 16px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
    
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background-color: #12192b;
        border-color: #243049;
    }

    /* Thinking process (proces uvažovania) */
    .streamlit-expanderHeader {
        background: #090e18 !important;
        border: 1px solid #1e293b !important;
        border-radius: 10px !important;
        color: #38bdf8 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 0.85rem !important;
    }
    .streamlit-expanderContent {
        background: #080c14 !important;
        border: 1px solid #1e293b !important;
        border-top: none !important;
        border-radius: 0 0 10px 10px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.8rem !important;
        color: #94a3b8 !important;
    }

    /* Čipy pre webové zdroje */
    .source-chip {
        display: inline-flex;
        align-items: center;
        background: #101626;
        border: 1px solid #1e293b;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.75rem;
        color: #38bdf8;
        text-decoration: none;
        margin-right: 6px;
        margin-bottom: 6px;
        transition: all 0.2s;
    }
    .source-chip:hover {
        background: #17223b;
        border-color: #38bdf8;
        color: #7dd3fc;
    }

    /* Vstupný chat input */
    [data-testid="stChatInput"] {
        border-radius: 16px;
        border: 1px solid #1e293b;
        background: #0f1523 !important;
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: #06b6d4 !important;
        box-shadow: 0 0 0 1px #06b6d4 !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. Systémové inštrukcie pre režimy Polaris AI
# -----------------------------------------------------------------------------
SYSTEM_PROMPTS = {
    "nova": (
        "You are Polaris AI, an exceptionally intelligent, refined, and versatile conversational assistant. "
        "Your goal is to communicate with effortless clarity, warmth, and precision. "
        "Format your responses cleanly using Markdown, bullet points, and code blocks with syntax highlighting. "
        "Be concise when asked simple questions, and remarkably thorough on deep technical topics."
    ),
    "thinker": (
        "You are Polaris AI in Deep Reasoning Mode. "
        "For every complex question, STEM problem, or architectural challenge, you ALWAYS think step-by-step. "
        "You must enclose your entire reasoning, edge-case verification, and calculations strictly inside an opening <thought> and closing </thought> tag at the very start of your answer. "
        "After the </thought> tag, provide your definitive, crystal-clear, well-formatted final response."
    ),
    "architect": (
        "You are Polaris AI in Architect Mode, an elite principal full-stack software engineer. "
        "You specialize in clean architecture, production-grade code, and interactive visual artifacts. "
        "When asked to write code or create web demos, provide complete, self-contained, working HTML/CSS/JS or SVG blocks. "
        "Always label your code blocks with their exact language identifier (e.g., ```html, ```javascript, ```python, ```svg)."
    ),
    "scholar": (
        "You are Polaris AI in Scholar Mode, an academic research specialist. "
        "Provide deeply grounded, comprehensive explanations, analytical comparisons, and cite principles, historical context, and empirical data."
    )
}

# -----------------------------------------------------------------------------
# 4. Inicializácia stavu aplikácie (Session State)
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# 5. Získanie API Kľúča
# -----------------------------------------------------------------------------
api_key = os.environ.get("GEMINI_API_KEY") or (st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else "")

# -----------------------------------------------------------------------------
# 6. Bočný panel: Nový Chat, História, Režimy a Prílohy
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 12px;'>
        <div style='width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, #06b6d4, #2563eb); display: flex; align-items: center; justify-content: center; font-size: 18px;'>
            ✨
        </div>
        <div>
            <div style='font-size: 16px; font-weight: 700; color: #f8fafc; font-family: "Space Grotesk", sans-serif;'>POLARIS AI</div>
            <div style='font-size: 10px; font-family: monospace; color: #38bdf8;'>GEMINI 3.8 FLASH</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tlačidlo na Nový Chat
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

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Výber režimu inteligencie
    mode_options = {
        "nova": "⚡ Polaris Nova (Rýchly & Všestranný)",
        "thinker": "🧠 Polaris Thinker (Hĺbkové Uvažovanie)",
        "architect": "🛠️ Polaris Architect (Programovanie & Canvas)",
        "scholar": "📚 Polaris Scholar (Výskum & Citácie)"
    }
    
    current_mode = current_conv.get("mode", "nova")
    selected_mode_key = st.selectbox(
        "Model / Režim:",
        options=list(mode_options.keys()),
        format_func=lambda k: mode_options[k],
        index=list(mode_options.keys()).index(current_mode) if current_mode in mode_options else 0
    )
    current_conv["mode"] = selected_mode_key

    # Google Search prepínač
    web_search = st.toggle("🌐 Google Search Grounding", value=current_conv.get("web_search", False))
    current_conv["web_search"] = web_search

    # Nahranie súboru alebo obrázku
    uploaded_file = st.file_uploader(
        "📎 Priložiť obrázok alebo súbor:",
        type=["png", "jpg", "jpeg", "webp", "txt", "py", "js", "html", "json", "md"]
    )

    st.markdown("---")

    # Zoznam histórie konverzácií
    st.markdown("<div style='font-size: 11px; font-weight: 600; text-transform: uppercase; color: #64748b; font-family: monospace; margin-bottom: 8px;'>História Chatov</div>", unsafe_allow_html=True)
    
    sorted_conv_ids = sorted(
        st.session_state.conversations.keys(),
        key=lambda x: int(x.split("_")[1]) if "_" in x else 0,
        reverse=True
    )

    for cid in sorted_conv_ids:
        c = st.session_state.conversations[cid]
        is_active = (cid == active_id)
        
        col_chat, col_del = st.columns([8, 2])
        with col_chat:
            label = f"{'✨ ' if is_active else '💬 '}{c['title'][:22]}"
            if st.button(label, key=f"btn_{cid}", use_container_width=True):
                st.session_state.active_conv_id = cid
                st.session_state.active_artifact = c.get("artifact", None)
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"del_{cid}", help="Zmazať"):
                del st.session_state.conversations[cid]
                if cid == active_id:
                    remaining = list(st.session_state.conversations.keys())
                    st.session_state.active_conv_id = remaining[0] if remaining else "conv_" + str(int(time.time()))
                st.rerun()

    st.markdown("---")
    
    if not api_key:
        api_key_input = st.text_input("🔑 Zadaj Gemini API kľúč:", type="password")
        if api_key_input:
            api_key = api_key_input
            os.environ["GEMINI_API_KEY"] = api_key
            st.success("API kľúč uložený!")

    # Export chatu
    if st.button("📥 Exportovať chat (JSON)", use_container_width=True):
        chat_export = json.dumps(current_conv, indent=2, ensure_ascii=False)
        st.download_button(
            label="Stiahnuť JSON",
            data=chat_export,
            file_name=f"polaris_chat_{active_id}.json",
            mime="application/json",
            use_container_width=True
        )

# -----------------------------------------------------------------------------
# 7. Pomocné funkcie: Extrakcia Canvas Artifactov a Tvorba Názvu
# -----------------------------------------------------------------------------
def extract_artifact(text: str):
    html_match = re.search(r"```(?:html|htm)\s*([\s\S]*?)```", text, re.IGNORECASE)
    if html_match:
        return {"type": "html", "code": html_match.group(1).strip(), "title": "Web / HTML Interactive Canvas"}
    
    svg_match = re.search(r"```(?:svg)\s*([\s\S]*?)```", text, re.IGNORECASE) or re.search(r"(<svg[\s\S]*?<\/svg>)", text, re.IGNORECASE)
    if svg_match:
        return {"type": "svg", "code": svg_match.group(1).strip(), "title": "Vector SVG Canvas"}
    
    return None

def auto_generate_title(client: genai.Client, first_prompt: str) -> str:
    try:
        res = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=f"Vytvor stručný 3-4 slovný názov pre konverzáciu: '{first_prompt[:200]}'"
        )
        return res.text.strip().replace('"', '') if res.text else "Nová konverzácia"
    except Exception:
        return first_prompt[:25] + "..."

# -----------------------------------------------------------------------------
# 8. Horná navigačná lišta
# -----------------------------------------------------------------------------
top_col1, top_col2 = st.columns([7, 3])
with top_col1:
    st.markdown(f"### ✨ **{current_conv.get('title', 'Polaris AI')}**")
with top_col2:
    mode_name = current_conv.get("mode", "nova").capitalize()
    canvas_active = st.session_state.active_artifact is not None
    
    col_badge, col_canvas_toggle = st.columns([1, 1])
    with col_badge:
        st.markdown(f"""
        <div style='text-align: right; padding-top: 5px;'>
            <span style='background: #111827; border: 1px solid #1f2937; color: #38bdf8; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-family: monospace;'>
                MOD: {mode_name}
            </span>
        </div>
        """, unsafe_allow_html=True)
    with col_canvas_toggle:
        if canvas_active:
            if st.button("🖥️ Canvas Náhľad", use_container_width=True):
                st.session_state.show_canvas = not st.session_state.show_canvas
                st.rerun()

# -----------------------------------------------------------------------------
# 9. Rozdelenie obrazovky: Chat a Interaktívny Canvas
# -----------------------------------------------------------------------------
show_split = st.session_state.show_canvas and st.session_state.active_artifact is not None

if show_split:
    chat_container, canvas_container = st.columns([6, 5])
else:
    chat_container = st.container()

# -----------------------------------------------------------------------------
# 10. Chat Zóna & Správy
# -----------------------------------------------------------------------------
with chat_container:
    messages = current_conv.get("messages", [])

    # Úvodná obrazovka s inšpiračnými kartami
    if len(messages) == 0:
        st.markdown("""
        <div style='text-align: center; padding: 40px 10px 30px 10px;'>
            <div style='display: inline-block; padding: 16px; border-radius: 20px; background: radial-gradient(circle, rgba(6,182,212,0.15) 0%, rgba(11,15,23,0) 70%); margin-bottom: 12px;'>
                <span style='font-size: 40px;'>✨</span>
            </div>
            <h2 style='color: #f8fafc; font-family: "Space Grotesk", sans-serif; font-size: 28px; margin-bottom: 8px;'>
                Kam ťa má <span style='background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>Polaris</span> dnes viesť?
            </h2>
            <p style='color: #94a3b8; font-size: 14px; max-width: 540px; margin: 0 auto 30px auto;'>
                Vysoko inteligentný asistent s transparentným uvažovaním, živým náhľadom kódu v Canvase a vyhľadávaním na webe.
            </p>
        </div>
        """, unsafe_allow_html=True)

        sc1, sc2 = st.columns(2)
        with sc1:
            if st.button("🎮 **Interaktívna Arkádová Hra**\n\nNaprogramuj hrateľnú retro Breakout hru v jednom HTML/JS bloku", use_container_width=True):
                st.session_state.starter_prompt = "Naprogramuj v jednom self-contained HTML/CSS/JavaScript bloku plne hrateľnú retro arkádovú hru Neon Breakout s plynulou fyzikou, efektmi pri zrážke loptičky s tehlami, zvukovými tónmi a počítadlom skóre."
                current_conv["mode"] = "architect"
                st.rerun()
            if st.button("🧠 **Hĺbková Matematická Analýza**\n\nOdvoď dôkaz Eulerovej rovnice e^(iπ) + 1 = 0 krok po kroku", use_container_width=True):
                st.session_state.starter_prompt = "Vysvetli a matematicky odvoď Eulerovu identitu e^(i*pi) + 1 = 0 krok po kroku. Uvažuj analyticky a ukáž rotáciu v komplexnej rovine."
                current_conv["mode"] = "thinker"
                st.rerun()
        with sc2:
            if st.button("⚡ **Architektúra Distribuovaného Systému**\n\nNavrhni škálovateľný real-time editor v Reacte a WebSockets", use_container_width=True):
                st.session_state.starter_prompt = "Navrhni produkčnú systémovú architektúru pre real-time kolaboratívny editor dokumentov (štýl Google Docs). Porovnaj CRDT vs Operational Transformation (OT) a WebSocket topológiu."
                current_conv["mode"] = "architect"
                st.rerun()
            if st.button("🌐 **Najnovšie Objavovanie Vesmíru**\n\nVyhľadaj aktuálne astronomické objavy tohto roka s citáciami", use_container_width=True):
                st.session_state.starter_prompt = "Vyhľadaj na webe najdôležitejšie astronomické objavy a pozorovania teleskopov z tohto roka. Zhrň kľúčové fakty s overenými zdrojmi a odkazmi."
                current_conv["mode"] = "scholar"
                current_conv["web_search"] = True
                st.rerun()

    # Vykreslenie histórie správ
    for idx, msg in enumerate(messages):
        role = msg["role"]
        is_assistant = (role == "assistant")
        
        with st.chat_message(role, avatar="✨" if is_assistant else None):
            if msg.get("image_bytes"):
                st.image(msg["image_bytes"], width=250, caption="Priložený obrázok")
                
            content = msg["content"]
            
            # Zobrazenie uvažovania v rozklikávacom expanderi
            thought_match = re.search(r"<thought>([\s\S]*?)</thought>", content)
            if thought_match:
                thought_text = thought_match.group(1).strip()
                clean_content = re.sub(r"<thought>[\s\S]*?</thought>", "", content).strip()
                
                with st.expander("🧠 Proces uvažovania (Thinking Process)", expanded=False):
                    st.markdown(f"```text\n{thought_text}\n```")
                st.markdown(clean_content)
            else:
                st.markdown(content)

            # Zobrazenie zdrojov z webu
            sources = msg.get("sources", [])
            if sources:
                st.markdown("<div style='margin-top: 10px; font-size: 11px; color: #64748b; font-weight: 600;'>CITOVANÉ ZDROJE:</div>", unsafe_allow_html=True)
                chips_html = "".join([
                    f"<a href='{s.get('url', '#')}' target='_blank' class='source-chip'>🔗 {s.get('title', 'Zdroj')[:30]}</a>"
                    for s in sources
                ])
                st.markdown(chips_html, unsafe_allow_html=True)

            # Tlačidlo na spustenie Canvasu pri vygenerovanom kóde
            msg_artifact = extract_artifact(content)
            if msg_artifact and is_assistant:
                col_btn, _ = st.columns([3, 7])
                with col_btn:
                    if st.button(f"🚀 Spustiť v Canvase ({msg_artifact['type'].upper()})", key=f"art_btn_{idx}"):
                        st.session_state.active_artifact = msg_artifact
                        current_conv["artifact"] = msg_artifact
                        st.session_state.show_canvas = True
                        st.rerun()

# -----------------------------------------------------------------------------
# 11. Interaktívny Canvas (Spustenie aplikácie/kódu v prehliadači)
# -----------------------------------------------------------------------------
if show_split:
    with canvas_container:
        artifact = st.session_state.active_artifact
        st.markdown(f"""
        <div style='background: #0f1523; border: 1px solid #1e293b; border-radius: 12px; padding: 12px 16px; margin-bottom: 12px;'>
            <span style='font-size: 13px; font-weight: 600; color: #38bdf8;'>🖥️ POLARIS INTERACTIVE CANVAS</span>
            <div style='font-size: 11px; color: #94a3b8;'>{artifact.get('title', 'Živý náhľad kódu')}</div>
        </div>
        """, unsafe_allow_html=True)

        tab_preview, tab_code = st.tabs(["▶️ Živý Náhľad", "💻 Zdrojový Kód"])
        
        with tab_preview:
            raw_code = artifact.get("code", "")
            if artifact.get("type") == "svg":
                full_html = f"""<!DOCTYPE html><html><body style='margin:0; background:#0c0f17; display:flex; align-items:center; justify-content:center; min-height:100vh;'>{raw_code}</body></html>"""
            elif "<!DOCTYPE html>" in raw_code or "<html" in raw_code:
                full_html = raw_code
            else:
                full_html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><script src='https://cdn.tailwindcss.com'></script></head><body style='background:#0c0f17; color:#f1f5f9; padding:16px;'>{raw_code}</body></html>"""

            components.html(full_html, height=560, scrolling=True)

        with tab_code:
            st.code(raw_code, language=artifact.get("type", "html"))
            st.download_button(
                label="💾 Stiahnuť kód súboru",
                data=raw_code,
                file_name=f"polaris_artifact.{'html' if artifact.get('type') == 'html' else 'svg'}",
                mime="text/plain",
                use_container_width=True
            )

# -----------------------------------------------------------------------------
# 12. Spracovanie otázky a streamovanie odpovede
# -----------------------------------------------------------------------------
chat_input = st.chat_input("Opýtaj sa Polaris čokoľvek, požiadaj o kód alebo riešenie...")
prompt = chat_input or st.session_state.pop("starter_prompt", None)

if prompt:
    if not api_key:
        st.error("⚠️ Chýba Gemini API kľúč! Zadaj ho v ľavom bočnom paneli.")
        st.stop()

    image_bytes_to_save = None
    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        if uploaded_file.type.startswith("image/"):
            image_bytes_to_save = file_bytes
        else:
            text_data = file_bytes.decode("utf-8", errors="ignore")
            prompt = f"{prompt}\n\n--- Obsah priloženého súboru ({uploaded_file.name}) ---\n{text_data}"

    user_msg_entry = {
        "role": "user",
        "content": prompt,
        "image_bytes": image_bytes_to_save
    }
    messages.append(user_msg_entry)
    
    with chat_container:
        with st.chat_message("user"):
            if image_bytes_to_save:
                st.image(image_bytes_to_save, width=250)
            st.markdown(prompt)

    client = genai.Client(api_key=api_key)
    if len(messages) == 1:
        current_conv["title"] = auto_generate_title(client, prompt)

    with chat_container:
        with st.chat_message("assistant", avatar="✨"):
            msg_placeholder = st.empty()
            full_text = ""
            grounding_sources = []

            try:
                api_contents = []
                for m in messages:
                    parts = []
                    if m.get("image_bytes"):
                        parts.append(types.Part.from_bytes(data=m["image_bytes"], mime_type="image/png"))
                    if m.get("content"):
                        parts.append(types.Part.from_text(text=m["content"]))
                    
                    api_contents.append(
                        types.Content(
                            role="model" if m["role"] == "assistant" else "user",
                            parts=parts
                        )
                    )

                tools = [{"google_search": {}}] if current_conv.get("web_search") else None
                system_instruction = SYSTEM_PROMPTS.get(current_conv.get("mode", "nova"), SYSTEM_PROMPTS["nova"])

                stream = client.models.generate_content_stream(
                    model="gemini-3.8-flash",
                    contents=api_contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        tools=tools,
                        temperature=0.3 if current_conv.get("mode") == "thinker" else 0.7
                    )
                )

                for chunk in stream:
                    if chunk.candidates and chunk.candidates[0].grounding_metadata:
                        gm = chunk.candidates[0].grounding_metadata
                        if gm.grounding_chunks:
                            for c in gm.grounding_chunks:
                                if c.web and c.web.uri:
                                    grounding_sources.append({
                                        "title": c.web.title or "Zdroj",
                                        "url": c.web.uri
                                    })

                    if chunk.text:
                        full_text += chunk.text
                        msg_placeholder.markdown(full_text + " ▌")

                # Finálne vykreslenie s oddeleným uvažovaním
                thought_match = re.search(r"<thought>([\s\S]*?)</thought>", full_text)
                if thought_match:
                    thought_text = thought_match.group(1).strip()
                    clean_content = re.sub(r"<thought>[\s\S]*?</thought>", "", full_text).strip()
                    msg_placeholder.empty()
                    with st.expander("🧠 Proces uvažovania (Thinking Process)", expanded=False):
                        st.markdown(f"```text\n{thought_text}\n```")
                    st.markdown(clean_content)
                else:
                    msg_placeholder.markdown(full_text)

                # Zobrazenie zdrojov
                if grounding_sources:
                    st.markdown("<div style='margin-top: 10px; font-size: 11px; color: #64748b; font-weight: 600;'>CITOVANÉ ZDROJE:</div>", unsafe_allow_html=True)
                    chips_html = "".join([
                        f"<a href='{s['url']}' target='_blank' class='source-chip'>🔗 {s['title'][:30]}</a>"
                        for s in grounding_sources
                    ])
                    st.markdown(chips_html, unsafe_allow_html=True)

                # Detekcia interaktívneho artifactu (kódu)
                new_artifact = extract_artifact(full_text)
                if new_artifact:
                    st.session_state.active_artifact = new_artifact
                    current_conv["artifact"] = new_artifact
                    if current_conv.get("mode") == "architect":
                        st.session_state.show_canvas = True
                    st.rerun()

                messages.append({
                    "role": "assistant",
                    "content": full_text,
                    "sources": grounding_sources
                })

            except Exception as e:
                st.error(f"Chyba pri generovaní odpovede z Polaris AI: {e}")
