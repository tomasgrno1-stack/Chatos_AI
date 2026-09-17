# =============================================================================
# CHATOŠ AI — Špičkový Slovenský Umelo-Inteligentný Asistent
# =============================================================================
# Architektúra: Streamlit + Google Gemini API (google-genai SDK)
# Jazyk a Persona: Slovenčina, Striktný Mužský rod ("urobil som", "pripravil som")
# Funkcie:
#   - ChatGPT-like Obsidian Cyberpunk luxusný tmavý vizuál
#   - Živý Interaktívny Sandbox / Canvas (HTML, CSS, JS, SVG)
#   - Transparentné hĺbkové uvažovanie (Thinking Process v expanderi)
#   - Google Web Search Grounding s klikateľnými zdrojmi
#   - Multimodálne vstupy: Obrázky (Vision) a Kódové súbory
#   - Automatická ochrana pred 429 (Exponential Backoff & Fallback modely)
#   - Správa histórie chatov (Vytváranie, Premenovanie, Zmazanie, Export do JSON/MD)
# =============================================================================

import os
import re
import json
import time
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional

import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types

# -----------------------------------------------------------------------------
# 1. Konfigurácia Stránky Streamlit
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Chatoš AI — Inteligentný Asistent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. Prémiový Dizajn (Obsidian, Cyan & Indigo Cyber-Aesthetics)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --bg-main: #0a0d14;
        --bg-surface: #0f1422;
        --bg-card: #13192b;
        --border-subtle: #1e283d;
        --accent-cyan: #06b6d4;
        --accent-blue: #3b82f6;
        --accent-purple: #8b5cf6;
        --text-primary: #f8fafc;
        --text-secondary: #94a3b8;
    }

    .stApp {
        background: radial-gradient(circle at 50% 0%, #11182c 0%, #080b12 80%);
        color: var(--text-primary);
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    [data-testid="stSidebar"] {
        background-color: #080b12 !important;
        border-right: 1px solid #1a2236 !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: #1a2236;
        margin: 12px 0;
    }

    [data-testid="stSidebar"] .stButton>button {
        background-color: #101524;
        color: #e2e8f0;
        border: 1px solid #1f293d;
        border-radius: 12px;
        font-weight: 500;
        font-size: 0.85rem;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        text-align: left;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
    }

    [data-testid="stSidebar"] .stButton>button:hover {
        background-color: #172036;
        border-color: #38bdf8;
        color: #38bdf8;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(6, 182, 212, 0.15);
    }

    .btn-new-chat button {
        background: linear-gradient(135deg, #06b6d4 0%, #2563eb 100%) !important;
        color: #020617 !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
        border: none !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 18px rgba(6, 182, 212, 0.3) !important;
        transition: all 0.2s ease-in-out !important;
    }
    .btn-new-chat button:hover {
        transform: scale(1.02) !important;
        box-shadow: 0 6px 22px rgba(6, 182, 212, 0.45) !important;
    }

    [data-testid="stChatMessage"] {
        background: #0f1524;
        border: 1px solid #1a2338;
        border-radius: 18px;
        padding: 1.25rem 1.6rem;
        margin-bottom: 1.1rem;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25);
        backdrop-filter: blur(8px);
        transition: border-color 0.2s ease;
    }

    [data-testid="stChatMessage"]:hover {
        border-color: #2b3954;
    }

    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: linear-gradient(135deg, #13192c 0%, #161e36 100%);
        border-color: #273452;
    }

    .streamlit-expanderHeader {
        background: #090e1a !important;
        border: 1px solid #1e293f !important;
        border-radius: 12px !important;
        color: #38bdf8 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 8px 14px !important;
    }

    .streamlit-expanderContent {
        background: #060912 !important;
        border: 1px solid #1e293f !important;
        border-top: none !important;
        border-radius: 0 0 12px 12px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.82rem !important;
        color: #94a3b8 !important;
        padding: 14px !important;
    }

    .source-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #111728;
        border: 1px solid #1f2c45;
        padding: 5px 12px;
        border-radius: 10px;
        font-size: 0.76rem;
        color: #38bdf8;
        text-decoration: none;
        margin-right: 8px;
        margin-bottom: 8px;
        transition: all 0.2s ease;
    }
    .source-chip:hover {
        background: #19233d;
        border-color: #38bdf8;
        color: #7dd3fc;
        transform: translateY(-1px);
    }

    [data-testid="stChatInput"] {
        border-radius: 18px !important;
        border: 1px solid #222e47 !important;
        background: #0d121f !important;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4) !important;
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: #06b6d4 !important;
        box-shadow: 0 0 0 2px rgba(6, 182, 212, 0.25) !important;
    }

    code {
        font-family: 'JetBrains Mono', monospace !important;
        background-color: #121828 !important;
        padding: 2px 6px !important;
        border-radius: 6px !important;
        color: #38bdf8 !important;
    }

    .btn-launch-canvas button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 10px !important;
        font-size: 0.8rem !important;
        box-shadow: 0 3px 10px rgba(16, 185, 129, 0.25) !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. Systémové Inštrukcie — Striktný Mužský Rod & Persona Chatoš AI
# -----------------------------------------------------------------------------
BASE_MASCULINE_IDENTITY = (
    "Voláš sa Chatoš AI. Si elitný, inteligentný, mimoriadne schopný a príjemný umelo-inteligentný asistent. "
    "DÔLEŽITÉ GRAMATICKÉ PRAVIDLO: Vždy vystupuješ a vyjadruješ sa striktne V MUŽSKOM RODE (napríklad: "
    "'som pripravený', 'vytvoril som', 'analyzoval som', 'preveril som', 'rád ti pomôžem', 'myslel som', 'skontroloval som'). "
    "Nikdy nepoužívaj ženský ani neurčitý neosobný tvar pre seba. "
    "Tvoj tón je profesionálny, priateľský, bystrý, vecný a ochotný. "
    "Komunikuješ v čistom, modernom slovenskom jazyku s bezchybným formátovaním v Markdown."
)

SYSTEM_PROMPTS = {
    "nova": (
        f"{BASE_MASCULINE_IDENTITY} "
        "Si v režime 'Chatoš Nova' (Rýchly & Všestranný). "
        "Poskytuj jasné, priame, pohotové a výstižné odpovede na každodenné otázky a nápady."
    ),
    "thinker": (
        f"{BASE_MASCULINE_IDENTITY} "
        "Si v režime 'Chatoš Thinker' (Hĺbkové Transparentné Uvažovanie). "
        "Pri každej zložitejšej úlohe najprv uvažuj krok po kroku. "
        "Svoje vnútorné uvažovanie umiestni do otváracej značky <thought> a uzatváracej </thought> na začiatku odpovede. "
        "Až potom poskytni definitívnu a zrozumiteľnú odpoveď."
    ),
    "architect": (
        f"{BASE_MASCULINE_IDENTITY} "
        "Si v režime 'Chatoš Architect' (Hlavný Softvérový Inžinier a Architekt). "
        "Špecializuješ sa na písanie čistého, produkčného kódu. "
        "Keď tvoríš webové aplikácie, hry, nástroje alebo vizualizácie, vždy vygeneruj kompletný a samostatný blok kódu (```html s Tailwind/JS alebo ```svg). "
        "Vždy označ kód správnym identifikátorom (```html, ```python, ```javascript, ```typescript, ```css)."
    ),
    "scholar": (
        f"{BASE_MASCULINE_IDENTITY} "
        "Si v režime 'Chatoš Scholar' (Vedecký a Akademický Výskumník). "
        "Poskytuj hlboko vyargumentované, rigorózne a vyvážené odpovede s faktickou presnosťou."
    )
}

# -----------------------------------------------------------------------------
# 4. Inicializácia Pamäte (Session State)
# -----------------------------------------------------------------------------
if "conversations" not in st.session_state:
    st.session_state.conversations = {}

if "active_conv_id" not in st.session_state:
    initial_id = "chat_" + str(int(time.time()))
    st.session_state.conversations[initial_id] = {
        "title": "Nová konverzácia",
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "messages": [],
        "mode": "nova",
        "web_search": False,
        "artifact": None
    }
    st.session_state.active_conv_id = initial_id

if "active_artifact" not in st.session_state:
    st.session_state.active_artifact = None

if "show_canvas" not in st.session_state:
    st.session_state.show_canvas = False

active_id = st.session_state.active_conv_id
if active_id not in st.session_state.conversations:
    st.session_state.conversations[active_id] = {
        "title": "Nová konverzácia",
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "messages": [],
        "mode": "nova",
        "web_search": False,
        "artifact": None
    }

current_conv = st.session_state.conversations[active_id]

# -----------------------------------------------------------------------------
# 5. Bezpečné Načítanie API Kľúča
# -----------------------------------------------------------------------------
api_key = os.environ.get("GEMINI_API_KEY") or (st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else "")

# -----------------------------------------------------------------------------
# 6. Pomocné Funkcie
# -----------------------------------------------------------------------------
def detect_canvas_artifact(text: str) -> Optional[Dict[str, str]]:
    html_match = re.search(r"```(?:html|htm)\s*([\s\S]*?)```", text, re.IGNORECASE)
    if html_match and len(html_match.group(1).strip()) > 30:
        return {
            "type": "html",
            "code": html_match.group(1).strip(),
            "title": "Interaktívny Webový Náhľad (HTML/JS)"
        }
    
    svg_match = re.search(r"```(?:svg)\s*([\s\S]*?)```", text, re.IGNORECASE) or re.search(r"(<svg[\s\S]*?<\/svg>)", text, re.IGNORECASE)
    if svg_match:
        return {
            "type": "svg",
            "code": svg_match.group(1).strip(),
            "title": "Vektorová Grafika (SVG Canvas)"
        }
    return None

def clean_thought_tags(raw_text: str):
    thought_match = re.search(r"<thought>([\s\S]*?)</thought>", raw_text)
    if thought_match:
        return thought_match.group(1).strip(), re.sub(r"<thought>[\s\S]*?</thought>", "", raw_text).strip()
    return None, raw_text

def execute_gemini_stream(client: genai.Client, selected_model: str, api_contents: list, system_instruction: str, web_search_enabled: bool):
    models_sequence = [selected_model, "gemini-2.5-flash", "gemini-2.0-flash"]
    seen = set()
    models_to_try = [m for m in models_sequence if not (m in seen or seen.add(m))]
    tools = [{"google_search": {}}] if web_search_enabled else None

    for model_name in models_to_try:
        try:
            stream = client.models.generate_content_stream(
                model=model_name,
                contents=api_contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=tools,
                    temperature=0.7
                )
            )
            return stream, model_name, None
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                time.sleep(1)
                continue
            else:
                return None, model_name, str(e)

    return None, None, "Kvóta API kľúča je prečerpaná (Chyba 429)."

# -----------------------------------------------------------------------------
# 7. Bočný Panel: Nástroje a Nastavenia
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 15px; padding: 4px;'>
        <div style='width: 38px; height: 38px; border-radius: 10px; background: linear-gradient(135deg, #06b6d4, #3b82f6); display: flex; align-items: center; justify-content: center; font-size: 20px; box-shadow: 0 4px 14px rgba(6, 182, 212, 0.35);'>
            🤖
        </div>
        <div>
            <div style='font-size: 17px; font-weight: 800; color: #f8fafc; font-family: "Space Grotesk", sans-serif;'>CHATOŠ AI</div>
            <div style='font-size: 10px; font-family: monospace; color: #38bdf8;'>SLOVENSKÝ ASISTENT &middot; PRO</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='btn-new-chat'>", unsafe_allow_html=True)
    if st.button("➕ Nová konverzácia", use_container_width=True):
        new_conv_id = "chat_" + str(int(time.time()))
        st.session_state.conversations[new_conv_id] = {
            "title": "Nová konverzácia",
            "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "messages": [],
            "mode": current_conv.get("mode", "nova"),
            "web_search": current_conv.get("web_search", False),
            "artifact": None
        }
        st.session_state.active_conv_id = new_conv_id
        st.session_state.active_artifact = None
        st.session_state.show_canvas = False
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    available_models = {
        "gemini-2.5-flash": "⚡ Gemini 2.5 Flash (Najvyššia kvóta)",
        "gemini-3.8-flash": "🚀 Gemini 3.8 Flash (Najnovší)",
        "gemini-2.5-pro": "🧠 Gemini 2.5 Pro (Hĺbková logika)"
    }
    selected_model = st.selectbox(
        "Model Gemini:",
        options=list(available_models.keys()),
        format_func=lambda m: available_models[m],
        index=0
    )

    mode_titles = {
        "nova": "⚡ Chatoš Nova (Všestranný)",
        "thinker": "🧠 Chatoš Thinker (Uvažovanie)",
        "architect": "🛠️ Chatoš Architect (Programovanie & Canvas)",
        "scholar": "📚 Chatoš Scholar (Veda & Výskum)"
    }
    selected_mode = st.selectbox(
        "Režim inteligencie:",
        options=list(mode_titles.keys()),
        format_func=lambda k: mode_titles[k],
        index=list(mode_titles.keys()).index(current_conv.get("mode", "nova")) if current_conv.get("mode") in mode_titles else 0
    )
    current_conv["mode"] = selected_mode

    web_grounding = st.toggle("🌐 Google Search Grounding", value=current_conv.get("web_search", False))
    current_conv["web_search"] = web_grounding

    attached_file = st.file_uploader(
        "📎 Priložiť obrázok alebo kód:",
        type=["png", "jpg", "jpeg", "webp", "txt", "py", "js", "html", "css", "json", "md"]
    )

    st.markdown("---")
    st.markdown("<div style='font-size: 11px; font-weight: 700; text-transform: uppercase; color: #64748b; font-family: monospace; margin-bottom: 8px;'>História Konverzácií</div>", unsafe_allow_html=True)
    
    sorted_ids = sorted(st.session_state.conversations.keys(), key=lambda x: int(x.split("_")[1]) if "_" in x else 0, reverse=True)

    for cid in sorted_ids:
        c_data = st.session_state.conversations[cid]
        is_current = (cid == active_id)
        chat_col, del_col = st.columns([8, 2])
        with chat_col:
            prefix = "🤖 " if is_current else "💬 "
            display_title = c_data["title"][:22] + ("..." if len(c_data["title"]) > 22 else "")
            if st.button(f"{prefix}{display_title}", key=f"nav_{cid}", use_container_width=True):
                st.session_state.active_conv_id = cid
                st.session_state.active_artifact = c_data.get("artifact", None)
                st.rerun()
        with del_col:
            if st.button("🗑️", key=f"rm_{cid}", help="Zmazať"):
                del st.session_state.conversations[cid]
                if cid == active_id:
                    remaining = list(st.session_state.conversations.keys())
                    st.session_state.active_conv_id = remaining[0] if remaining else "chat_" + str(int(time.time()))
                st.rerun()

    st.markdown("---")

    if not api_key:
        new_key = st.text_input("🔑 Vlož svoj Gemini API kľúč:", type="password")
        if new_key:
            api_key = new_key
            os.environ["GEMINI_API_KEY"] = new_key
            st.success("Kľúč bol uložený!")
            st.rerun()
    else:
        with st.expander("⚙️ Zmena API Kľúča"):
            override_key = st.text_input("Nový kľúč:", type="password")
            if st.button("Uložiť nový kľúč") and override_key:
                os.environ["GEMINI_API_KEY"] = override_key
                st.success("Nový API kľúč aktivovaný!")
                st.rerun()

    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        st.download_button(
            label="📥 Export JSON",
            data=json.dumps(current_conv, indent=2, ensure_ascii=False),
            file_name=f"chatos_{active_id}.json",
            mime="application/json",
            use_container_width=True
        )
    with exp_col2:
        if st.button("🧹 Vymazať správy", use_container_width=True):
            current_conv["messages"] = []
            current_conv["artifact"] = None
            st.session_state.active_artifact = None
            st.session_state.show_canvas = False
            st.rerun()

# -----------------------------------------------------------------------------
# 8. Horná Lišta
# -----------------------------------------------------------------------------
header_left, header_right = st.columns([7, 3])
with header_left:
    st.markdown(f"### 🤖 **{current_conv.get('title', 'Chatoš AI')}**")
with header_right:
    m_name = current_conv.get("mode", "nova").capitalize()
    has_artifact = st.session_state.active_artifact is not None
    badge_col, toggle_col = st.columns([1, 1])
    with badge_col:
        st.markdown(f"""
        <div style='text-align: right; padding-top: 6px;'>
            <span style='background: #101626; border: 1px solid #1f2a40; color: #38bdf8; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-family: monospace;'>
                CHATOŠ &middot; {m_name}
            </span>
        </div>
        """, unsafe_allow_html=True)
    with toggle_col:
        if has_artifact:
            if st.button("🖥️ Živý Canvas", use_container_width=True):
                st.session_state.show_canvas = not st.session_state.show_canvas
                st.rerun()

# -----------------------------------------------------------------------------
# 9. Rozvrhnutie Obrazovky
# -----------------------------------------------------------------------------
is_split_view = st.session_state.show_canvas and st.session_state.active_artifact is not None
chat_viewport, canvas_viewport = st.columns([6, 5]) if is_split_view else (st.container(), None)

# -----------------------------------------------------------------------------
# 10. Chat Zóna
# -----------------------------------------------------------------------------
with chat_viewport:
    messages = current_conv.get("messages", [])

    if len(messages) == 0:
        st.markdown("""
        <div style='text-align: center; padding: 40px 10px 30px 10px;'>
            <div style='display: inline-block; padding: 18px; border-radius: 22px; background: radial-gradient(circle, rgba(6,182,212,0.18) 0%, rgba(11,15,23,0) 70%); margin-bottom: 12px;'>
                <span style='font-size: 42px;'>🤖</span>
            </div>
            <h2 style='color: #f8fafc; font-family: "Space Grotesk", sans-serif; font-size: 30px; font-weight: 700; margin-bottom: 6px;'>
                Ahoj! Som <span style='background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>Chatoš AI</span>
            </h2>
            <p style='color: #94a3b8; font-size: 15px; max-width: 580px; margin: 0 auto 30px auto;'>
                Som tvoj osobný inteligentný asistent. Pripravil som pre teba špičkové uvažovanie, programovanie s Canvasom a hľadanie na webe. S čím ti dnes pomôžem?
            </p>
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🎮 **Naprogramuj hrateľnú retro Breakout hru**\n\nKompletná hra v HTML/JS s fyzikou a skóre", use_container_width=True):
                st.session_state.auto_prompt = "Naprogramuj v jednom HTML/CSS/JS bloku kompletnú hrateľnú retro Breakout hru s loptičkou, tehlami a skóre."
                current_conv["mode"] = "architect"
                st.rerun()
            if st.button("🧠 **Matematická analýza Eulerovej rovnice**\n\nOdvoď vzťah e^(iπ) + 1 = 0 krok po kroku", use_container_width=True):
                st.session_state.auto_prompt = "Vysvetli a matematicky odvoď Eulerovu identitu e^(i*pi) + 1 = 0 krok po kroku. Uvažuj hĺbkovo a analyticky."
                current_conv["mode"] = "thinker"
                st.rerun()
        with c2:
            if st.button("⚡ **Navrhni distribuovanú architektúru**\n\nReal-time systém s WebSockets a Redisom", use_container_width=True):
                st.session_state.auto_prompt = "Navrhni produkčnú systémovú architektúru pre globálny real-time chat s WebSockets a Redisom."
                current_conv["mode"] = "architect"
                st.rerun()
            if st.button("🌐 **Vyhľadaj novinky vo vesmírnom výskume**\n\nZisti aktuálne astronomické objavy tohto roka", use_container_width=True):
                st.session_state.auto_prompt = "Vyhľadaj na webe najdôležitejšie astronomické objavy tohto roka s citáciami overených zdrojov."
                current_conv["mode"] = "scholar"
                current_conv["web_search"] = True
                st.rerun()

    for idx, msg in enumerate(messages):
        role = msg["role"]
        is_bot = (role == "assistant")
        with st.chat_message(role, avatar="🤖" if is_bot else None):
            if msg.get("image_bytes"):
                st.image(msg["image_bytes"], width=260)
                
            content = msg["content"]
            thought, final_answer = clean_thought_tags(content)
            if thought:
                with st.expander("🧠 Proces uvažovania Chatoša (Thinking Process)", expanded=False):
                    st.markdown(f"```text\n{thought}\n```")
                st.markdown(final_answer)
            else:
                st.markdown(content)

            sources = msg.get("sources", [])
            if sources:
                st.markdown("<div style='margin-top: 10px; font-size: 11px; color: #64748b; font-weight: 700;'>CITOVANÉ ZDROJE:</div>", unsafe_allow_html=True)
                chips = "".join([f"<a href='{s.get('url', '#')}' target='_blank' class='source-chip'>🔗 {s.get('title', 'Zdroj')[:32]}</a>" for s in sources])
                st.markdown(chips, unsafe_allow_html=True)

            artifact = detect_canvas_artifact(content)
            if artifact and is_bot:
                st.markdown("<div class='btn-launch-canvas'>", unsafe_allow_html=True)
                if st.button(f"🚀 Spustiť v Canvase ({artifact['type'].upper()})", key=f"art_btn_{idx}"):
                    st.session_state.active_artifact = artifact
                    current_conv["artifact"] = artifact
                    st.session_state.show_canvas = True
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 11. Živý Canvas
# -----------------------------------------------------------------------------
if is_split_view and canvas_viewport:
    with canvas_viewport:
        active_art = st.session_state.active_artifact
        st.markdown(f"""
        <div style='background: #0d121f; border: 1px solid #1e283d; border-radius: 14px; padding: 14px 18px; margin-bottom: 12px;'>
            <span style='font-size: 14px; font-weight: 700; color: #38bdf8;'>🖥️ CHATOŠ INTERACTIVE CANVAS</span>
            <div style='font-size: 11px; color: #94a3b8;'>{active_art.get('title', 'Náhľad')}</div>
        </div>
        """, unsafe_allow_html=True)

        tab_live, tab_src = st.tabs(["▶️ Živý Náhľad", "💻 Zdrojový Kód"])
        with tab_live:
            code_str = active_art.get("code", "")
            if active_art.get("type") == "svg":
                html_code = f"<!DOCTYPE html><html><body style='margin:0; background:#0a0d14; display:flex; align-items:center; justify-content:center; min-height:100vh;'>{code_str}</body></html>"
            elif "<!DOCTYPE html>" in code_str or "<html" in code_str:
                html_code = code_str
            else:
                html_code = f"<!DOCTYPE html><html><head><script src='https://cdn.tailwindcss.com'></script></head><body style='background:#0a0d14; color:#f8fafc; padding:16px;'>{code_str}</body></html>"

            components.html(html_code, height=580, scrolling=True)

        with tab_src:
            st.code(code_str, language=active_art.get("type", "html"))
            st.download_button(
                label="💾 Stiahnuť súbor kódu",
                data=code_str,
                file_name=f"chatos_export.{'html' if active_art.get('type') == 'html' else 'svg'}",
                mime="text/plain",
                use_container_width=True
            )

# -----------------------------------------------------------------------------
# 12. Spracovanie a Generovanie
# -----------------------------------------------------------------------------
user_prompt_input = st.chat_input("Napíš Chatošovi čokoľvek, požiadaj o kód alebo analýzu...")
active_prompt = user_prompt_input or st.session_state.pop("auto_prompt", None)

if active_prompt:
    if not api_key:
        st.error("⚠️ Zadaj Gemini API kľúč v ľavom bočnom paneli.")
        st.stop()

    saved_image_bytes = None
    if attached_file is not None:
        raw_bytes = attached_file.getvalue()
        if attached_file.type.startswith("image/"):
            saved_image_bytes = raw_bytes
        else:
            decoded = raw_bytes.decode("utf-8", errors="ignore")
            active_prompt = f"{active_prompt}\n\n--- Priložený súbor ({attached_file.name}) ---\n{decoded}"

    messages.append({"role": "user", "content": active_prompt, "image_bytes": saved_image_bytes})
    if len(messages) == 1:
        current_conv["title"] = active_prompt[:25] + ("..." if len(active_prompt) > 25 else "")

    with chat_viewport:
        with st.chat_message("user"):
            if saved_image_bytes:
                st.image(saved_image_bytes, width=260)
            st.markdown(active_prompt)

    genai_client = genai.Client(api_key=api_key)

    with chat_viewport:
        with st.chat_message("assistant", avatar="🤖"):
            response_placeholder = st.empty()
            accumulated_response = ""
            grounded_sources = []

            formatted_contents = []
            for msg_item in messages:
                parts = []
                if msg_item.get("image_bytes"):
                    parts.append(types.Part.from_bytes(data=msg_item["image_bytes"], mime_type="image/png"))
                if msg_item.get("content"):
                    parts.append(types.Part.from_text(text=msg_item["content"]))
                formatted_contents.append(types.Content(role="model" if msg_item["role"] == "assistant" else "user", parts=parts))

            active_instruction = SYSTEM_PROMPTS.get(current_conv.get("mode", "nova"), SYSTEM_PROMPTS["nova"])

            stream_result, used_model, stream_error = execute_gemini_stream(
                client=genai_client,
                selected_model=selected_model,
                api_contents=formatted_contents,
                system_instruction=active_instruction,
                web_search_enabled=current_conv.get("web_search", False)
            )

            if stream_result is not None:
                try:
                    for chunk in stream_result:
                        if chunk.candidates and chunk.candidates[0].grounding_metadata:
                            meta = chunk.candidates[0].grounding_metadata
                            if meta.grounding_chunks:
                                for c in meta.grounding_chunks:
                                    if c.web and c.web.uri:
                                        grounded_sources.append({"title": c.web.title or "Zdroj", "url": c.web.uri})

                        if chunk.text:
                            accumulated_response += chunk.text
                            response_placeholder.markdown(accumulated_response + " ▌")
                except Exception as stream_err:
                    accumulated_response += f"\n\n*(Generovanie prerušené: {stream_err})*"

                final_thought, final_text = clean_thought_tags(accumulated_response)
                response_placeholder.empty()
                if final_thought:
                    with st.expander("🧠 Proces uvažovania Chatoša (Thinking Process)", expanded=False):
                        st.markdown(f"```text\n{final_thought}\n```")
                    st.markdown(final_text)
                else:
                    st.markdown(accumulated_response)

                if grounded_sources:
                    st.markdown("<div style='margin-top: 10px; font-size: 11px; color: #64748b; font-weight: 700;'>CITOVANÉ ZDROJE:</div>", unsafe_allow_html=True)
                    chips = "".join([f"<a href='{s['url']}' target='_blank' class='source-chip'>🔗 {s['title'][:32]}</a>" for s in grounded_sources])
                    st.markdown(chips, unsafe_allow_html=True)

                new_art = detect_canvas_artifact(accumulated_response)
                if new_art:
                    st.session_state.active_artifact = new_art
                    current_conv["artifact"] = new_art
                    if current_conv.get("mode") == "architect":
                        st.session_state.show_canvas = True
                    st.rerun()

                messages.append({"role": "assistant", "content": accumulated_response, "sources": grounded_sources})
            else:
                response_placeholder.empty()
                st.error(f"""
                🛑 **Chyba: {stream_error}**
                
                1. ⏳ **Počkaj 30–60 sekúnd** (minútový limit bezplatného API sa resetuje).
                2. 🔑 Alebo vlož **nový API kľúč** z [Google AI Studio](https://aistudio.google.com/app/apikey) v bočnom paneli ("Zmena API Kľúča").
                3. ⚡ V bočnom paneli zvoľ model **Gemini 2.5 Flash**.
                """)
                if messages and messages[-1]["role"] == "user":
                    messages.pop()
