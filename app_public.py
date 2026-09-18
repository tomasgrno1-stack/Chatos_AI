# =============================================================================
# CHATOŠ AI — Špičkový Slovenský Umelo-Inteligentný Asistent
# =============================================================================
# Architektúra: Streamlit + Google Gemini API (google-genai SDK)
# Jazyk a Persona: Slovenčina, Striktný Mužský rod ("urobil som", "pripravil som")
# Funkcie:
#   - ŽIADNE zadávanie API kľúča v rozhraní (automatické načítanie bez obťažovania)
#   - ChatGPT-like Obsidian Cyberpunk luxusný tmavý vizuál
#   - Živý Interaktívny Sandbox / Canvas (HTML, CSS, JS, SVG)
#   - Transparentné hĺbkové uvažovanie (Thinking Process v expanderi)
#   - Google Web Search Grounding s klikateľnými zdrojmi
#   - Multimodálne vstupy: Obrázky (Vision) a Kódové súbory
#   - Automatická ochrana pred 429 (Exponential Backoff & Fallback modely)
#   - Správa histórie chatov (Vytváranie, Premenovanie, Zmazanie, Export)
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
# 1. Konfigurácia Stránky Streamlit (musí byť prvá)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Chatoš AI — Inteligentný Asistent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 0. Inteligentná Detekcia a Rotácia Viacerých API Kľúčov zo Secrets
# -----------------------------------------------------------------------------
# Ak chceš kľúče vložiť priamo do kódu, môžeš sem zadať jeden alebo viac:
HARDCODED_API_KEY = ""

def extract_all_keys_from_obj(obj: Any, depth: int = 0) -> List[str]:
    """Rekurzívne nájde všetky API kľúče (zoznamy, čiarkami oddelené reťazce, slovníky)."""
    keys = []
    if obj is None or depth > 6:
        return keys

    # Ak je to priamo string (môže byť jeden kľúč alebo viacero oddelených čiarkou/novým riadkom)
    if isinstance(obj, str):
        parts = re.split(r'[,;\n\r\t]+', obj)
        for p in parts:
            cleaned = p.strip().strip('"').strip("'")
            if cleaned.startswith("AIza") and len(cleaned) >= 28:
                keys.append(cleaned)
            elif len(cleaned) >= 35 and re.match(r'^[A-Za-z0-9_-]+$', cleaned):
                keys.append(cleaned)
        return keys

    # Ak je to zoznam alebo tuple (napr. GEMINI_API_KEYS = ["AIza...", "AIza..."])
    if isinstance(obj, (list, tuple)):
        for item in obj:
            keys.extend(extract_all_keys_from_obj(item, depth + 1))
        return keys

    # Ak je to dict-like (st.secrets, AttrDict, konfigurácie)
    if isinstance(obj, dict) or hasattr(obj, "items") or hasattr(obj, "keys"):
        try:
            items = list(obj.items())
        except Exception:
            items = []

        for k, v in items:
            k_lower = str(k).lower().strip()
            # Ak hodnota je priamo string alebo štruktúra
            if isinstance(v, str):
                parts = re.split(r'[,;\n\r\t]+', v)
                for p in parts:
                    cleaned = p.strip().strip('"').strip("'")
                    if cleaned.startswith("AIza") and len(cleaned) >= 28:
                        keys.append(cleaned)
                    elif any(t in k_lower for t in ["gemini", "google", "api_key", "apikey", "key"]) and len(cleaned) >= 20:
                        keys.append(cleaned)
            else:
                keys.extend(extract_all_keys_from_obj(v, depth + 1))

    return keys

def get_all_gemini_api_keys() -> List[str]:
    """Automaticky získa všetky platné unikátne Gemini API kľúče z ľubovoľného zdroja."""
    collected = []

    # 1. Zadané v relácii (session state)
    if "session_api_key" in st.session_state and st.session_state["session_api_key"].strip():
        collected.extend(extract_all_keys_from_obj(st.session_state["session_api_key"]))

    # 2. Z hardcoded premennej v kóde
    if HARDCODED_API_KEY:
        collected.extend(extract_all_keys_from_obj(HARDCODED_API_KEY))

    # 3. Zo systémových premenných prostredia
    for env_var in [
        "GEMINI_API_KEYS", "GEMINI_API_KEY", "GOOGLE_API_KEY", "API_KEYS", 
        "GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"
    ]:
        env_val = os.environ.get(env_var, "")
        if env_val:
            collected.extend(extract_all_keys_from_obj(env_val))

    # 4. Zo Streamlit Secrets (hĺbková detekcia zoznamov aj jednotlivých kľúčov)
    try:
        if hasattr(st, "secrets"):
            collected.extend(extract_all_keys_from_obj(st.secrets))
    except Exception:
        pass

    # Odstránenie duplicít so zachovaním poradia
    unique_keys = []
    seen = set()
    for k in collected:
        if k and k not in seen:
            seen.add(k)
            unique_keys.append(k)

    return unique_keys

def get_gemini_api_key() -> str:
    """Vráti primárny kľúč (alebo prázdny reťazec, ak žiaden neexistuje)."""
    keys = get_all_gemini_api_keys()
    return keys[0] if keys else ""

def inspect_secrets_structure() -> Dict[str, Any]:
    """Zistí bezpečne aké kľúče a sekcie sa nachádzajú v st.secrets bez odhalenia tajomstiev."""
    diagnostics = {
        "has_secrets": False,
        "keys_found": [],
        "total_api_keys_loaded": len(get_all_gemini_api_keys()),
        "error": None
    }
    try:
        if hasattr(st, "secrets"):
            diagnostics["has_secrets"] = True
            try:
                for k in st.secrets.keys():
                    diagnostics["keys_found"].append(str(k))
            except Exception as e:
                diagnostics["error"] = str(e)
    except Exception as e:
        diagnostics["error"] = str(e)
    return diagnostics

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
        "model": "gemini-3.8-flash",
        "web_search": False,
        "artifact": None
    }
    st.session_state.active_conv_id = initial_id

if "active_artifact" not in st.session_state:
    st.session_state.active_artifact = None

if "show_canvas" not in st.session_state:
    st.session_state.show_canvas = False

if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "user_name": "",
        "user_role": "",
        "custom_instructions": ""
    }

active_id = st.session_state.active_conv_id
if active_id not in st.session_state.conversations:
    st.session_state.conversations[active_id] = {
        "title": "Nová konverzácia",
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "messages": [],
        "mode": "nova",
        "model": "gemini-3.8-flash",
        "web_search": False,
        "artifact": None
    }

current_conv = st.session_state.conversations[active_id]

# -----------------------------------------------------------------------------
# 5. Pomocné Funkcie
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

def generate_smart_title(user_text: str) -> str:
    """Vytvorí výstižný, krátky 2-5 slovný názov konverzácie bez uvádzacích fráz."""
    clean = re.sub(
        r'^(ahoj|čau|prosím|vedel by si|chcel by som|chcem|povedz mi|vysvetli|napíš|sprav|vytvor|ukáž|ako|prečo|čo je|aký je)\s+',
        '',
        user_text.strip(),
        flags=re.IGNORECASE
    ).strip()
    if len(clean) < 3:
        clean = user_text.strip()
    first_line = clean.split("\n")[0]
    words = first_line.split()
    if len(words) > 5:
        smart = " ".join(words[:5]) + "..."
    else:
        smart = first_line[:32]
    return smart[:32].capitalize() if smart else "Konverzácia"

def generate_conversation_markdown(conv: Dict[str, Any]) -> str:
    """Vygeneruje čistý, formátovaný Markdown dokument z celej konverzácie."""
    title = conv.get("title", "Konverzácia Chatoš AI")
    created = conv.get("created_at", "")
    model = conv.get("model", "gemini-3.8-flash")
    mode = conv.get("mode", "nova")

    lines = [
        f"# {title}",
        f"*{created} | Model: {model} | Režim: Chatoš {mode.capitalize()}*",
        "",
        "---",
        ""
    ]
    for msg in conv.get("messages", []):
        role_title = "👤 Používateľ" if msg.get("role") == "user" else "🤖 Chatoš AI"
        lines.append(f"### {role_title}\n")
        if msg.get("file_name"):
            lines.append(f"📎 *Priložený súbor: {msg['file_name']}*\n")
        lines.append(msg.get("content", "").strip())
        lines.append("\n\n---\n")
    return "\n".join(lines)

def robust_stream_generator(api_keys: List[str], selected_model: str, api_contents: list, system_instruction: str, web_search_enabled: bool):
    """
    Mimoriadne odolný streamovací generátor s automatickým opakovaním (retry),
    striedaním viacerých kľúčov a záchranným prepínaním medzi stabilnými modelmi Gemini 2.5 Flash / 3.8 Flash / 2.5 Pro.
    """
    # Aktuálne oficiálne podporované modely Google Gemini API
    supported_models = ["gemini-2.5-flash", "gemini-3.8-flash", "gemini-3.1-pro-preview"]
    
    # Zoradíme: najprv používateľom zvolený model, potom ostatné ako záchranné zálohy
    models_to_try = [selected_model] + [m for m in supported_models if m != selected_model]
    tools = [{"google_search": {}}] if web_search_enabled else None

    detailed_errors = []

    for model_idx, model_name in enumerate(models_to_try):
        for key_idx, key in enumerate(api_keys):
            # Pre každý kľúč skúsime až 2 pokusy (s krátkou 1.5s pauzou pri 503/429)
            for attempt in range(2):
                try:
                    client = genai.Client(api_key=key)
                    stream = client.models.generate_content_stream(
                        model=model_name,
                        contents=api_contents,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            tools=tools,
                            temperature=0.7
                        )
                    )

                    # Overíme, či model odpovedá (chyba 503 sa často vyvolá pri prvom chunku)
                    stream_iter = iter(stream)
                    try:
                        first_chunk = next(stream_iter)
                    except StopIteration:
                        return
                    except Exception as chunk_exc:
                        err_msg = str(chunk_exc)
                        err_lower = err_msg.lower()
                        detailed_errors.append(f"• Model `{model_name}` (kľúč #{key_idx+1}, pokus {attempt+1}): {err_msg}")

                        if ("503" in err_lower or "unavailable" in err_lower or "high demand" in err_lower or "429" in err_lower or "resource_exhausted" in err_lower) and attempt == 0:
                            time.sleep(1.5)
                            continue
                        else:
                            break

                    # Úspech! Zostavíme prípadnú informačnú poznámku pre používateľa
                    fallback_note = None
                    if model_idx > 0 and model_name != selected_model:
                        fallback_note = f"ℹ️ Model `{selected_model}` bol na serveroch Google dočasne preťažený. Odpoveď bola bleskovo a úspešne doručená cez záložný model `{model_name}`."
                    elif key_idx > 0:
                        fallback_note = f"ℹ️ Kľúč #1 dosiahol limit kvóty. Chatoš automaticky a úspešne pokračoval cez kľúč #{key_idx+1}."

                    yield ("chunk", first_chunk, model_name, fallback_note)
                    for chunk in stream_iter:
                        yield ("chunk", chunk, model_name, None)
                    return

                except Exception as conn_exc:
                    err_msg = str(conn_exc)
                    err_lower = err_msg.lower()
                    detailed_errors.append(f"• Model `{model_name}` (kľúč #{key_idx+1}, pokus {attempt+1}): {err_msg}")

                    if ("503" in err_lower or "unavailable" in err_lower or "high demand" in err_lower or "429" in err_lower or "resource_exhausted" in err_lower) and attempt == 0:
                        time.sleep(1.5)
                        continue
                    else:
                        break

    # Ak všetky pokusy zlyhali, vrátime ucelený diagnostický prehľad
    errors_summary = "\n".join(detailed_errors[-4:]) if detailed_errors else "Neznáma chyba spojenia"
    yield ("error", None, None, errors_summary)

# -----------------------------------------------------------------------------
# 6. Bočný Panel: Nástroje a Nastavenia (BEZ OTÁZOK NA API KĽÚČ)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 15px; padding: 4px;'>
        <div style='width: 38px; height: 38px; border-radius: 10px; background: linear-gradient(135deg, #06b6d4, #3b82f6); display: flex; align-items: center; justify-content: center; font-size: 20px; box-shadow: 0 4px 14px rgba(6, 182, 212, 0.35);'>
            🤖
        </div>
        <div>
            <div style='font-size: 17px; font-weight: 800; color: #f8fafc; font-family: "Space Grotesk", sans-serif;'>CHATOŠ AI</div>
            <div style='font-size: 10px; font-family: monospace; color: #38bdf8;'>VŽDY PRIPRAVENÝ &middot; PRO</div>
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
            "model": current_conv.get("model", "gemini-3.8-flash"),
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
        "gemini-3.8-flash": "🚀 Gemini 3.8 Flash (Predvolený & Najnovší)",
        "gemini-2.5-flash": "⚡ Gemini 2.5 Flash (Rýchly & Stabilný)",
        "gemini-3.1-pro-preview": "🧠 Gemini 3.1 Pro (Hĺbková logika & Kód)"
    }
    model_keys = list(available_models.keys())
    saved_model = current_conv.get("model", "gemini-3.8-flash")
    if saved_model not in model_keys:
        saved_model = "gemini-3.8-flash"
        current_conv["model"] = saved_model
    default_model_idx = model_keys.index(saved_model)
    selected_model = st.selectbox(
        "Model Gemini:",
        options=model_keys,
        format_func=lambda m: available_models[m],
        index=default_model_idx
    )
    current_conv["model"] = selected_model

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

    with st.expander("🧠 Osobný profil a pamäť", expanded=False):
        st.caption("Chatoš si tieto informácie zapamätá a prispôsobí im svoje odpovede vo všetkých četoch.")
        p_name = st.text_input("Tvoje meno:", value=st.session_state.user_profile.get("user_name", ""), placeholder="napr. Rado", key="prof_name_in")
        p_role = st.text_input("Profesia / zameranie:", value=st.session_state.user_profile.get("user_role", ""), placeholder="napr. Python programátor, študent...", key="prof_role_in")
        p_instr = st.text_area("Inštrukcie pre štýl odpovedí:", value=st.session_state.user_profile.get("custom_instructions", ""), placeholder="napr. Odpovedaj stručne a vecne, píš príklady kódu...", key="prof_instr_in", height=80)
        st.session_state.user_profile["user_name"] = p_name
        st.session_state.user_profile["user_role"] = p_role
        st.session_state.user_profile["custom_instructions"] = p_instr

    attached_file = st.file_uploader(
        "📎 Priložiť súbor (PDF, Obrázok, Kód, CSV):",
        type=["png", "jpg", "jpeg", "webp", "pdf", "txt", "py", "js", "html", "css", "json", "md", "csv"]
    )

    st.markdown("---")
    st.markdown("<div style='font-size: 11px; font-weight: 700; text-transform: uppercase; color: #64748b; font-family: monospace; margin-bottom: 8px;'>História Konverzácií</div>", unsafe_allow_html=True)
    
    search_query = st.text_input("🔍 Hľadať...", placeholder="Hľadať v správach...", label_visibility="collapsed", key="search_chats_input")

    sorted_ids = sorted(st.session_state.conversations.keys(), key=lambda x: int(x.split("_")[1]) if "_" in x else 0, reverse=True)

    if search_query.strip():
        q_lower = search_query.strip().lower()
        filtered_ids = [
            cid for cid in sorted_ids
            if q_lower in st.session_state.conversations[cid].get("title", "").lower()
            or any(q_lower in m.get("content", "").lower() for m in st.session_state.conversations[cid].get("messages", []))
        ]
    else:
        filtered_ids = sorted_ids

    if search_query.strip() and not filtered_ids:
        st.caption("Žiadna konverzácia nezodpovedá hľadaniu.")

    for cid in filtered_ids:
        c_data = st.session_state.conversations[cid]
        is_current = (cid == active_id)
        chat_col, del_col = st.columns([8, 2])
        with chat_col:
            prefix = "🤖 " if is_current else "💬 "
            display_title = c_data["title"][:20] + ("..." if len(c_data["title"]) > 20 else "")
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

    # Zobrazenie stavu pripojenia API kľúča (s podporou viacerých kľúčov)
    all_keys_list = get_all_gemini_api_keys()
    if all_keys_list:
        k_count = len(all_keys_list)
        if k_count == 1:
            k_badge_text = "1 API kľúč aktívny"
        elif k_count in [2, 3, 4]:
            k_badge_text = f"{k_count} API kľúče (Auto-rotácia)"
        else:
            k_badge_text = f"{k_count} API kľúčov (Auto-rotácia)"

        st.markdown(f"""
        <div style='display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 12px; background: #0c121e; border: 1px solid #1a263c; border-radius: 10px;'>
            <div style='display: flex; align-items: center; gap: 8px;'>
                <div style='width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981;'></div>
                <span style='font-size: 12px; font-family: monospace; color: #38bdf8;'>Chatoš AI je pripojený</span>
            </div>
            <span style='font-size: 10.5px; font-family: monospace; color: #10b981; background: #052e24; border: 1px solid #0f766e; padding: 1px 7px; border-radius: 6px;'>{k_badge_text}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #1c1309; border: 1px solid #78350f; border-radius: 10px;'>
            <div style='width: 8px; height: 8px; border-radius: 50%; background: #f59e0b; box-shadow: 0 0 8px #f59e0b;'></div>
            <span style='font-size: 12px; font-family: monospace; color: #fbbf24;'>Kľúč nebol nájdený</span>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("🔑 Vložiť kľúč priamo tu", expanded=False):
            manual_key_val = st.text_input("Zadaj Gemini API kľúč:", type="password", key="side_key_in", placeholder="AIzaSy...")
            if st.button("Uložiť a aktivovať", key="btn_save_side_key", use_container_width=True):
                if manual_key_val.strip():
                    st.session_state["session_api_key"] = manual_key_val.strip()
                    st.rerun()

    exp_col1, exp_col2, exp_col3 = st.columns(3)
    with exp_col1:
        st.download_button(
            label="📥 JSON",
            data=json.dumps(current_conv, indent=2, ensure_ascii=False),
            file_name=f"chatos_{active_id}.json",
            mime="application/json",
            use_container_width=True,
            help="Stiahnuť konverzáciu v JSON formáte"
        )
    with exp_col2:
        st.download_button(
            label="📝 .MD",
            data=generate_conversation_markdown(current_conv),
            file_name=f"chatos_{active_id}.md",
            mime="text/markdown",
            use_container_width=True,
            help="Stiahnuť ako čistý Markdown dokument"
        )
    with exp_col3:
        if st.button("🧹 Zmazať", use_container_width=True, help="Vymazať správy aktuálneho četu"):
            current_conv["messages"] = []
            current_conv["artifact"] = None
            st.session_state.active_artifact = None
            st.session_state.show_canvas = False
            st.rerun()

# -----------------------------------------------------------------------------
# 7. Horná Lišta
# -----------------------------------------------------------------------------
header_left, header_right = st.columns([7, 3])
with header_left:
    st.markdown(f"### 🤖 **{current_conv.get('title', 'Chatoš AI')}**")
with header_right:
    m_name = current_conv.get("mode", "nova").capitalize()
    has_artifact = st.session_state.active_artifact is not None
    badge_col, toggle_col = st.columns([1, 1])
    with badge_col:
        model_display = current_conv.get('model', 'gemini-3.8-flash').replace('gemini-', '').replace('-flash', '').upper()
        st.markdown(f"""
        <div style='text-align: right; padding-top: 6px;'>
            <span style='background: #101626; border: 1px solid #1f2a40; color: #38bdf8; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-family: monospace;'>
                CHATOŠ &middot; {m_name} &middot; {model_display}
            </span>
        </div>
        """, unsafe_allow_html=True)
    with toggle_col:
        if has_artifact:
            if st.button("🖥️ Živý Canvas", use_container_width=True):
                st.session_state.show_canvas = not st.session_state.show_canvas
                st.rerun()

# -----------------------------------------------------------------------------
# 8. Rozvrhnutie Obrazovky
# -----------------------------------------------------------------------------
is_split_view = st.session_state.show_canvas and st.session_state.active_artifact is not None
chat_viewport, canvas_viewport = st.columns([6, 5]) if is_split_view else (st.container(), None)

# -----------------------------------------------------------------------------
# 9. Chat Zóna
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
                Som tvoj osobný inteligentný asistent. Som plne pripravený riešiť úlohy, písať kód so živým spustením v Canvase a hľadať informácie na webe. S čím ti dnes pomôžem?
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
            if msg.get("pdf_bytes") or (msg.get("file_name") and msg.get("file_name", "").lower().endswith(".pdf")):
                f_name = msg.get("file_name", "Dokument.pdf")
                st.markdown(f"<div style='display:inline-flex; align-items:center; gap:8px; background:#1e293b; border:1px solid #38bdf8; padding:6px 14px; border-radius:8px; margin-bottom:10px;'><span style='font-size:18px;'>📄</span><span style='font-size:13px; font-weight:600; color:#38bdf8;'>Priložený PDF dokument: {f_name}</span></div>", unsafe_allow_html=True)
            elif msg.get("file_name") and not msg.get("image_bytes"):
                f_name = msg.get("file_name")
                st.markdown(f"<div style='display:inline-flex; align-items:center; gap:8px; background:#1e293b; border:1px solid #475569; padding:5px 12px; border-radius:8px; margin-bottom:8px;'><span style='font-size:16px;'>📎</span><span style='font-size:12px; font-weight:500; color:#94a3b8;'>{f_name}</span></div>", unsafe_allow_html=True)
                
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

            # Panel rýchlych akcií pod odpoveďou asistenta
            if is_bot and content.strip() and not content.startswith("🛑"):
                st.markdown("<div style='margin-top: 12px; margin-bottom: 4px;'></div>", unsafe_allow_html=True)
                qa_c1, qa_c2, qa_c3, qa_c4 = st.columns([1.1, 1.1, 1.3, 1.4])
                with qa_c1:
                    if st.button("📋 Kopírovať", key=f"btn_copy_{idx}", help="Zobraziť čistý text na kopírovanie"):
                        st.session_state[f"show_copy_{idx}"] = not st.session_state.get(f"show_copy_{idx}", False)
                with qa_c2:
                    if st.button("⚡ Zhrnúť", key=f"btn_sum_{idx}", help="Zhrnúť odpoveď do 3 kľúčových bodov"):
                        st.session_state.auto_prompt = "Zhrň svoju predchádzajúcu odpoveď do 3 stručných a najdôležitejších bodov."
                        st.rerun()
                with qa_c3:
                    if st.button("💡 Zjednodušiť", key=f"btn_simp_{idx}", help="Vysvetliť jednoducho pre začiatočníka"):
                        st.session_state.auto_prompt = "Vysvetli svoju predchádzajúcu odpoveď ešte jednoduchšie a priateľskejšie, ako pre úplného začiatočníka."
                        st.rerun()
                with qa_c4:
                    if st.button("❓ Minikvíz", key=f"btn_quiz_{idx}", help="3 otázky na overenie pochopenia"):
                        st.session_state.auto_prompt = "Priprav mi 3 krátke otázky alebo minikvíz k tomu, čo si práve vysvetlil, aby som si preveril vedomosti."
                        st.rerun()

                if st.session_state.get(f"show_copy_{idx}", False):
                    st.code(final_answer, language="markdown")

# -----------------------------------------------------------------------------
# 10. Živý Canvas
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
# 11. Spracovanie a Generovanie (Bez zadávania kľúča)
# -----------------------------------------------------------------------------
user_prompt_input = st.chat_input("Napíš Chatošovi čokoľvek, požiadaj o kód alebo analýzu...")
active_prompt = user_prompt_input or st.session_state.pop("auto_prompt", None)

if active_prompt:
    # Ak kľúč náhodou chýba, poskytneme presnú diagnostiku a okamžitý fallback
    current_key = get_gemini_api_key()
    if not current_key:
        diag = inspect_secrets_structure()
        found_keys_list = diag.get("keys_found", [])
        
        with chat_viewport:
            st.markdown(f"""
            <div style='background: #161a26; border: 1px solid #28354f; border-radius: 16px; padding: 22px; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);'>
                <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 8px;'>
                    <span style='font-size: 24px;'>🔑</span>
                    <span style='font-size: 17px; font-weight: 700; color: #38bdf8;'>Pripojenie Gemini API Kľúča</span>
                </div>
                <p style='color: #cbd5e1; font-size: 13.5px; margin-bottom: 12px; line-height: 1.6;'>
                    Aplikácia automaticky prehľadala <code>st.secrets</code> aj systémové premenné, ale nenašla platný kľúč.
                </p>
                <div style='background: #090d16; border: 1px solid #1e293f; border-radius: 10px; padding: 12px 16px; font-family: monospace; font-size: 12.5px; color: #94a3b8; margin-bottom: 16px;'>
                    <div style='color: #64748b; font-size: 11px; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;'>Odporúčaný formát v Streamlit Secrets:</div>
                    <code style='color: #38bdf8; font-size: 13px;'>GEMINI_API_KEY = "AIzaSy..."</code>
                    <div style='margin-top: 8px; font-size: 11px; color: #64748b;'>
                        Stav secrets: {f"Detegované položky: {found_keys_list}" if found_keys_list else "st.secrets je prázdne (ešte sa nenačítalo)"}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("##### ⚡ Alebo vlož kľúč sem a spusti chat okamžite (bez reštartu):")
            c_input, c_btn = st.columns([4, 1])
            with c_input:
                temp_key = st.text_input(
                    "Zadaj svoj Gemini API kľúč:",
                    type="password",
                    placeholder="AIzaSy...",
                    key="temp_key_prompt",
                    label_visibility="collapsed"
                )
            with c_btn:
                if st.button("🚀 Spustiť", use_container_width=True, key="btn_activate_key_now"):
                    if temp_key.strip():
                        st.session_state["session_api_key"] = temp_key.strip()
                        st.session_state["auto_prompt"] = active_prompt
                        st.rerun()
                    else:
                        st.warning("Najprv vlož kľúč začínajúci na AIza...")
        st.stop()

    saved_image_bytes = None
    saved_pdf_bytes = None
    saved_file_name = None

    if attached_file is not None:
        raw_bytes = attached_file.getvalue()
        saved_file_name = attached_file.name
        f_type = attached_file.type or ""
        f_name_lower = attached_file.name.lower()

        if f_type.startswith("image/") or f_name_lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
            saved_image_bytes = raw_bytes
        elif f_type == "application/pdf" or f_name_lower.endswith(".pdf"):
            saved_pdf_bytes = raw_bytes
        else:
            decoded = raw_bytes.decode("utf-8", errors="ignore")
            active_prompt = f"{active_prompt}\n\n--- Priložený dokument ({attached_file.name}) ---\n{decoded}"

    messages.append({
        "role": "user",
        "content": active_prompt,
        "image_bytes": saved_image_bytes,
        "pdf_bytes": saved_pdf_bytes,
        "file_name": saved_file_name
    })

    # Inteligentný AI názov konverzácie
    if len(messages) <= 2 or current_conv.get("title", "") in ["Nová konverzácia", ""]:
        current_conv["title"] = generate_smart_title(active_prompt)

    with chat_viewport:
        with st.chat_message("user"):
            if saved_image_bytes:
                st.image(saved_image_bytes, width=260)
            if saved_pdf_bytes:
                st.markdown(f"<div style='display:inline-flex; align-items:center; gap:8px; background:#1e293b; border:1px solid #38bdf8; padding:6px 14px; border-radius:8px; margin-bottom:10px;'><span style='font-size:18px;'>📄</span><span style='font-size:13px; font-weight:600; color:#38bdf8;'>Priložený PDF dokument: {saved_file_name}</span></div>", unsafe_allow_html=True)
            elif saved_file_name and not saved_image_bytes:
                st.markdown(f"<div style='display:inline-flex; align-items:center; gap:8px; background:#1e293b; border:1px solid #475569; padding:5px 12px; border-radius:8px; margin-bottom:8px;'><span style='font-size:16px;'>📎</span><span style='font-size:12px; font-weight:500; color:#94a3b8;'>{saved_file_name}</span></div>", unsafe_allow_html=True)
            st.markdown(active_prompt)

    all_available_keys = get_all_gemini_api_keys()

    with chat_viewport:
        with st.chat_message("assistant", avatar="🤖"):
            response_placeholder = st.empty()
            accumulated_response = ""
            grounded_sources = []

            formatted_contents = []
            for msg_item in messages:
                raw_text = msg_item.get("content", "")
                # Ignorujeme prerušené chybové hlásenia z predchádzajúcich pokusov
                if "Generovanie prerušené:" in raw_text or "🛑 Chyba" in raw_text:
                    continue
                parts = []
                if msg_item.get("image_bytes"):
                    parts.append(types.Part.from_bytes(data=msg_item["image_bytes"], mime_type="image/png"))
                if msg_item.get("pdf_bytes"):
                    parts.append(types.Part.from_bytes(data=msg_item["pdf_bytes"], mime_type="application/pdf"))
                if raw_text:
                    parts.append(types.Part.from_text(text=raw_text))
                if parts:
                    formatted_contents.append(types.Content(role="model" if msg_item["role"] == "assistant" else "user", parts=parts))

            # Zakomponovanie profilu a trvalej pamäte používateľa do systémových inštrukcií
            user_memory_parts = []
            if st.session_state.user_profile.get("user_name"):
                user_memory_parts.append(f"Používateľ sa volá {st.session_state.user_profile['user_name']}.")
            if st.session_state.user_profile.get("user_role"):
                user_memory_parts.append(f"Profesia/zameranie používateľa: {st.session_state.user_profile['user_role']}.")
            if st.session_state.user_profile.get("custom_instructions"):
                user_memory_parts.append(f"Trvalé osobné inštrukcie a preferencie pre odpovede: {st.session_state.user_profile['custom_instructions']}.")

            memory_prompt = ("\n\nPOUŽÍVATEĽSKÝ PROFIL A PREFERENCIE: " + " ".join(user_memory_parts)) if user_memory_parts else ""
            active_instruction = SYSTEM_PROMPTS.get(current_conv.get("mode", "nova"), SYSTEM_PROMPTS["nova"]) + memory_prompt

            generator = robust_stream_generator(
                api_keys=all_available_keys,
                selected_model=selected_model,
                api_contents=formatted_contents,
                system_instruction=active_instruction,
                web_search_enabled=current_conv.get("web_search", False)
            )

            success = False
            active_fallback_notice = None

            for event_type, chunk_data, used_model, extra_info in generator:
                if event_type == "chunk":
                    success = True
                    if extra_info:
                        active_fallback_notice = extra_info

                    chunk = chunk_data
                    if chunk.candidates and chunk.candidates[0].grounding_metadata:
                        meta = chunk.candidates[0].grounding_metadata
                        if meta.grounding_chunks:
                            for c in meta.grounding_chunks:
                                if c.web and c.web.uri:
                                    grounded_sources.append({"title": c.web.title or "Zdroj", "url": c.web.uri})

                    if chunk.text:
                        accumulated_response += chunk.text
                        response_placeholder.markdown(accumulated_response + " ▌")

                elif event_type == "error":
                    response_placeholder.empty()
                    st.error(f"""
                    🛑 **Všetky pokusy o spojenie zlyhali:**
                    
                    {extra_info}
                    
                    ---
                    💡 **Ako to hneď vyriešiť:**
                    1. ⏳ **Dočasné preťaženie serverov Google (503):** Počkaj 5–10 sekúnd a odošli správu znova.
                    2. ⚡ **Zmena modelu:** V bočnom paneli prepni model na **Gemini 2.5 Flash** (má najvyššiu priepustnosť a stabilitu).
                    3. 🔑 **Dôležité info k viacerým API kľúčom:** Ak máš v Secrets viac kľúčov vytvorených v **rovnakom Google Cloud projekte**, zdieľajú rovnaký bezplatný limit (RPM). Aby mal každý kľúč samostatný plný limit, vytvor si nový projekt v [Google AI Studio](https://aistudio.google.com/) cez horné menu projektov.
                    """)
                    if messages and messages[-1]["role"] == "user":
                        messages.pop()
                    st.stop()

            if success and accumulated_response.strip():
                final_thought, final_text = clean_thought_tags(accumulated_response)
                response_placeholder.empty()

                if active_fallback_notice:
                    st.info(active_fallback_notice)

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
                st.rerun()
