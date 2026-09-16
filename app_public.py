import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import uuid
import pypdf
import docx
import pandas as pd
import requests
import threading
import time
import json
import io
import os
import datetime

# ==============================================================================
# 1. KONFIGURÁCIA STRÁNKY A ŠTÝLOV
# ==============================================================================

st.set_page_config(
    page_title="Polaris AI (Public Version)",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Vlastné CSS pre čisti minimalistický vzhľad
st.markdown("""
    <style>
    .stApp {
        background-color: #f9f9fb !important;
        color: #0d0d0d !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }

    [data-testid="stSidebar"] {
        background-color: #f3f3f7 !important;
        border-right: 1px solid #e5e5e5 !important;
        padding-top: 0.5rem;
    }

    #MainMenu, header, footer {visibility: hidden;}
    
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 5rem !important;
        max-width: 950px !important;
    }

    .hero-title {
        text-align: center;
        font-size: 2.2rem;
        font-weight: 600;
        color: #0d0d0d;
        margin-top: 8vh;
        margin-bottom: 1.5rem;
    }

    .public-badge {
        background-color: #e0f2fe;
        color: #0369a1;
        border-radius: 16px;
        padding: 6px 14px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
    }

    .sidebar-section-title {
        font-size: 0.8rem;
        color: #8e8e93;
        padding: 12px 12px 4px 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .anon-profile-card {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 6px;
        border-radius: 8px;
    }
    
    .avatar-circle-anon {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background-color: #64748b;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.85rem;
        font-weight: 600;
    }

    .settings-header {
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. KEEP-ALIVE PINGER SERVICE
# ==============================================================================

APP_URL = "https://polaris-ai.streamlit.app"

def keep_alive_worker():
    """Pozadový thread udržiavajúci aplikáciu v chode bez nutnosti prihlásenia."""
    while True:
        time.sleep(240)
        try:
            requests.get(APP_URL, timeout=10)
        except Exception:
            pass

if "pinger_started" not in st.session_state:
    st.session_state.pinger_started = True
    threading.Thread(target=keep_alive_worker, daemon=True).start()

# ==============================================================================
# 3. INITIALIZATION OF API CLIENT & MODELS
# ==============================================================================

if "GOOGLE_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Chýba GOOGLE_API_KEY v st.secrets! Pridajte API kľúč do nastavení Streamlitu.")
    st.stop()

MODELE = {
    "Gemini 2.5 Flash (Rýchly & Multimodálny)": "gemini-2.5-flash",
    "Gemini 2.5 Pro (Pokročilá logika a kódovanie)": "gemini-2.5-pro",
    "Gemini 1.5 Pro (Stabilný model)": "gemini-1.5-pro",
    "Gemini 1.5 Flash (Ľahký model)": "gemini-1.5-flash"
}

ROLY = {
    "Personal Assistant": """You are Polaris, an advanced AI assistant.
CRITICAL MANDATE:
Detect the exact language of the user's latest prompt and respond EXCLUSIVELY in that exact language (e.g. Slovak if Slovak, English if English, German if German). Never switch to another language.""",
    
    "Senior Software Engineer": """You are Polaris, a principal software architect and senior engineer.
CRITICAL MANDATE:
Detect and mirror the user's input language strictly.
Provide high quality, production-ready code with concise technical explanations.""",
    
    "Concise Assistant": """You are Polaris.
CRITICAL MANDATE:
Respond strictly in the user's prompt language.
Limit responses to a maximum of 2-3 sentences.""",

    "Data Analyst": """You are Polaris, a data analytics expert.
CRITICAL MANDATE:
Detect and mirror the user's input language strictly.
Analyze provided datasets, code snippets, or analytical queries accurately.""",

    "Creative Writer": """You are Polaris, a creative writing expert.
CRITICAL MANDATE:
Detect and mirror the user's input language strictly.
Generate expressive, fluid, and engaging prose."""
}

# ==============================================================================
# 4. ANONYMOUS SESSION STATE INITIALIZATION (BEZ PRIHLASOVANIA)
# ==============================================================================

def initialize_anon_session():
    # Automatické anonymné ID relácie pre každého návštevníka
    if "anon_user_id" not in st.session_state:
        st.session_state.anon_user_id = f"guest_{str(uuid.uuid4())[:8]}"
        
    if "chats" not in st.session_state:
        st.session_state.chats = {}
    if "archived_chats" not in st.session_state:
        st.session_state.archived_chats = {}
    if "current_chat_id" not in st.session_state:
        first_id = str(uuid.uuid4())
        st.session_state.chats[first_id] = {
            "title": "Nový konverzácia", 
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "messages": []
        }
        st.session_state.current_chat_id = first_id
        
    if "show_settings" not in st.session_state:
        st.session_state.show_settings = False
    if "settings_tab" not in st.session_state:
        st.session_state.settings_tab = "Všeobecné"
    if "top_tab" not in st.session_state:
        st.session_state.top_tab = "Chat"
    if "vybrana_rola" not in st.session_state:
        st.session_state.vybrana_rola = "Personal Assistant"
    if "vybrany_model" not in st.session_state:
        st.session_state.vybrany_model = "Gemini 2.5 Flash (Rýchly & Multimodálny)"
    if "enable_web_search" not in st.session_state:
        st.session_state.enable_web_search = True
    if "temperature" not in st.session_state:
        st.session_state.temperature = 0.7
    if "max_tokens" not in st.session_state:
        st.session_state.max_tokens = 8192
    if "system_prompt_custom" not in st.session_state:
        st.session_state.system_prompt_custom = ""
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "Svetlý"
    if "default_workspace" not in st.session_state:
        st.session_state.default_workspace = "Public Workspace"

initialize_anon_session()

# ==============================================================================
# 5. CHAT & DATA MANAGEMENT
# ==============================================================================

def vytvor_novy_chat():
    nove_id = str(uuid.uuid4())
    st.session_state.chats[nove_id] = {
        "title": "Nový konverzácia", 
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "messages": []
    }
    st.session_state.current_chat_id = nove_id

def archivuj_chat(chat_id):
    if chat_id in st.session_state.chats:
        st.session_state.archived_chats[chat_id] = st.session_state.chats[chat_id]
        del st.session_state.chats[chat_id]
        if st.session_state.current_chat_id == chat_id:
            if st.session_state.chats:
                st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]
            else:
                vytvor_novy_chat()

def obnov_chat_z_archivu(chat_id):
    if chat_id in st.session_state.archived_chats:
        st.session_state.chats[chat_id] = st.session_state.archived_chats[chat_id]
        del st.session_state.archived_chats[chat_id]
        st.session_state.current_chat_id = chat_id

def vymaz_chat(chat_id):
    if chat_id in st.session_state.chats:
        del st.session_state.chats[chat_id]
        if st.session_state.current_chat_id == chat_id:
            if st.session_state.chats:
                st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]
            else:
                vytvor_novy_chat()

def exportuj_chat_json(chat_id):
    if chat_id in st.session_state.chats:
        return json.dumps(st.session_state.chats[chat_id], ensure_ascii=False, indent=2)
    return ""

def exportuj_chat_markdown(chat_id):
    if chat_id in st.session_state.chats:
        chat_data = st.session_state.chats[chat_id]
        md = f"# {chat_data['title']}\n*Vytvorené: {chat_data.get('created_at', 'N/A')}*\n\n---\n\n"
        for m in chat_data["messages"]:
            role = "Užívateľ" if m["role"] == "user" else "Asistent"
            md += f"### {role}\n{m['content']}\n\n"
        return md
    return ""

# ==============================================================================
# 6. BOČNÝ PANEL (SIDEBAR)
# ==============================================================================

with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 4px 8px; margin-bottom: 8px;">
            <span style="font-weight: 600; font-size: 1.15rem; color: #1c1c1e;">Polaris AI ∨</span>
        </div>
    """, unsafe_allow_html=True)

    if st.button("📝 Nový čet", key="btn_new_chat_anon", use_container_width=True):
        vytvor_novy_chat()
        st.session_state.show_settings = False
        st.rerun()

    # Vyhľadávanie v nedávnych konverzáciách
    st.session_state.search_query = st.text_input("🔍 Hľadať v správach...", value=st.session_state.search_query, key="sidebar_search_anon")

    st.markdown("""
        <div style="padding: 6px 10px; font-size: 0.9rem; color: #2d2d2d;">🖼️ Obrázky a dokumenty</div>
        <div style="padding: 6px 10px; font-size: 0.9rem; color: #2d2d2d;">🌐 Vyhľadávanie na webe</div>
        <div class="sidebar-section-title">História relácie</div>
    """, unsafe_allow_html=True)

    # Zobrazenie filtrirovaného zoznamu
    filtered_chats = {}
    for cid, cdata in st.session_state.chats.items():
        if st.session_state.search_query.lower() in cdata["title"].lower():
            filtered_chats[cid] = cdata

    for chat_id, chat_data in list(filtered_chats.items()):
        is_active = (chat_id == st.session_state.current_chat_id)
        label = f"💬 {chat_data['title']}"
        
        col_btn, col_act = st.columns([0.80, 0.20])
        with col_btn:
            if st.button(label, key=f"select_{chat_id}", use_container_width=True, type="secondary" if not is_active else "primary"):
                st.session_state.current_chat_id = chat_id
                st.session_state.show_settings = False
                st.rerun()
        with col_act:
            with st.popover("⋮"):
                st.caption(f"Vytvorené: {chat_data.get('created_at', 'N/A')}")
                nove_meno = st.text_input("Prejmenovať", value=chat_data["title"], key=f"rename_in_{chat_id}")
                if st.button("Uložiť názov", key=f"save_name_{chat_id}"):
                    st.session_state.chats[chat_id]["title"] = nove_meno
                    st.rerun()
                
                st.divider()
                if st.button("📦 Archivovať", key=f"arch_{chat_id}"):
                    archivuj_chat(chat_id)
                    st.rerun()
                
                if st.button("🗑 Vymazať", key=f"del_{chat_id}"):
                    vymaz_chat(chat_id)
                    st.rerun()

    st.divider()

    # Karta anonymného hostinského profilu bez loginu
    col_prof1, col_prof2 = st.columns([0.82, 0.18])
    with col_prof1:
        st.markdown(f"""
            <div class="anon-profile-card">
                <div class="avatar-circle-anon">G</div>
                <div>
                    <div style="font-weight: 600; font-size: 0.85rem; color: #1c1c1e;">Host / Anonym</div>
                    <div style="font-size: 0.72rem; color: #64748b;">ID: {st.session_state.anon_user_id}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col_prof2:
        if st.button("⚙️", key="open_settings_anon_btn", help="Nastavenia"):
            st.session_state.show_settings = not st.session_state.show_settings
            st.rerun()

# ==============================================================================
# 7. NASTAVENIA (SETTINGS VIEW)
# ==============================================================================

if st.session_state.show_settings:
    col_back, _ = st.columns([0.2, 0.8])
    with col_back:
        if st.button("← Späť do chatu", key="close_settings_anon"):
            st.session_state.show_settings = False
            st.rerun()

    st.markdown("## ⚙️ Nastavenia Aplikácie")
    st.divider()

    col_set_nav, col_set_content = st.columns([0.30, 0.70])
    
    with col_set_nav:
        st.markdown("**Konfigurácia AI**")
        tabs_ai = ["Všeobecné", "Model & Engine", "Vzhľad", "Archivované čety"]
        for t_item in tabs_ai:
            if st.button(t_item, key=f"set_tab_{t_item}", use_container_width=True, type="primary" if st.session_state.settings_tab == t_item else "secondary"):
                st.session_state.settings_tab = t_item
                st.rerun()

    with col_set_content:
        st.markdown(f"<div class='settings-header'>{st.session_state.settings_tab}</div>", unsafe_allow_html=True)
        
        if st.session_state.settings_tab == "Všeobecné":
            st.markdown("#### Verejný Režim")
            st.info("Aplikácia beží bez potreby registrácie alebo prihlásenia. Konverzácie sú uložené lokálne vo vašom prehliadači.")
            st.toggle("Uložiť históriu počas relácie", value=True)

        elif st.session_state.settings_tab == "Model & Engine":
            st.markdown("#### Gemini API Engine")
            st.session_state.vybrany_model = st.selectbox("Model:", list(MODELE.keys()), index=list(MODELE.keys()).index(st.session_state.vybrany_model))
            st.session_state.enable_web_search = st.toggle("🌐 Google Search Grounding", value=st.session_state.enable_web_search)
            st.session_state.vybrana_rola = st.selectbox("Rola:", list(ROLY.keys()), index=list(ROLY.keys()).index(st.session_state.vybrana_rola))
            st.session_state.temperature = st.slider("Temperature:", 0.0, 1.0, st.session_state.temperature, 0.05)

        elif st.session_state.settings_tab == "Vzhľad":
            st.markdown("#### Téma rozhrania")
            st.session_state.theme_mode = st.radio("Farebný režim:", ["Svetlý", "Tmavý"])

        elif st.session_state.settings_tab == "Archivované čety":
            st.markdown("#### Archivované konverzácie")
            if not st.session_state.archived_chats:
                st.info("Žiadne archivované čety.")
            else:
                for arch_id, arch_data in list(st.session_state.archived_chats.items()):
                    col_a1, col_a2 = st.columns([0.7, 0.3])
                    with col_a1:
                        st.write(f"💬 **{arch_data['title']}**")
                    with col_a2:
                        if st.button("Obnoviť", key=f"rest_{arch_id}"):
                            obnov_chat_z_archivu(arch_id)
                            st.rerun()

# ==============================================================================
# 8. HLAVNÝ CHAT WORKSPACE
# ==============================================================================

else:
    col_top1, col_top2, col_top3 = st.columns([0.25, 0.50, 0.25])
    with col_top1:
        st.markdown('<div class="public-badge">🌐 Public Access (No Login)</div>', unsafe_allow_html=True)
    with col_top2:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💬 Chat", use_container_width=True, type="primary" if st.session_state.top_tab == "Chat" else "secondary"):
                st.session_state.top_tab = "Chat"
                st.rerun()
        with c2:
            if st.button("🛠️ IDE / Kódovanie", use_container_width=True, type="primary" if st.session_state.top_tab == "Work" else "secondary"):
                st.session_state.top_tab = "Work"
                st.rerun()

    if st.session_state.top_tab == "Work":
        st.markdown("### 🛠️ Kódovací editor pre hostí")
        st.text_area("Kód Python:", value="print('Aplikácia beží bez prihlasovania!')", height=300)
    else:
        aktualny_chat = st.session_state.chats[st.session_state.current_chat_id]

        if not aktualny_chat["messages"]:
            st.markdown('<div class="hero-title">Môžeme začať, keď budeš chcieť.</div>', unsafe_allow_html=True)

        # Exporty chatu
        if aktualny_chat["messages"]:
            col_exp1, col_exp2, _ = st.columns([0.2, 0.2, 0.6])
            with col_exp1:
                st.download_button("📥 JSON", data=exportuj_chat_json(st.session_state.current_chat_id), file_name="chat.json", mime="application/json")
            with col_exp2:
                st.download_button("📝 Markdown", data=exportuj_chat_markdown(st.session_state.current_chat_id), file_name="chat.md", mime="text/markdown")

        # História správ
        for msg in aktualny_chat["messages"]:
            with st.chat_message(msg["role"]):
                if "image" in msg and msg["image"] is not None:
                    st.image(msg["image"], use_container_width=True)
                if "file_info" in msg and msg["file_info"]:
                    st.caption(f"📎 Príloha: **{msg['file_info']}**")
                st.markdown(msg["content"])

        # Vstupný panel
        col_plus, col_in = st.columns([0.07, 0.93])
        uploaded_file = None
        with col_plus:
            with st.popover("➕"):
                uploaded_file = st.file_uploader(
                    "Príloha:",
                    type=["png", "jpg", "jpeg", "mp3", "wav", "mp4", "txt", "pdf", "docx", "xlsx", "csv"],
                    key=f"anon_up_{st.session_state.current_chat_id}"
                )

        with col_in:
            prompt = st.chat_input("Názov alebo správu...")

        if prompt:
            if len(aktualny_chat["messages"]) == 0:
                aktualny_chat["title"] = prompt[:25] + "..." if len(prompt) > 25 else prompt

            sprava_pouzivatela = {"role": "user", "content": prompt}
            parts_list = []

            if uploaded_file is not None:
                subor_typ = uploaded_file.type
                nazov_suboru = uploaded_file.name
                sprava_pouzivatela["file_info"] = nazov_suboru

                if subor_typ in ["image/png", "image/jpeg", "image/jpg"]:
                    img = Image.open(uploaded_file)
                    parts_list.append(img)
                    sprava_pouzivatela["image"] = img

                elif subor_typ in ["audio/mp3", "audio/wav", "video/mp4"]:
                    subor_bytes = uploaded_file.read()
                    parts_list.append(types.Part.from_bytes(data=subor_bytes, mime_type=subor_typ))

                elif subor_typ == "text/plain":
                    parts_list.append(f"Text ({nazov_suboru}):\n{uploaded_file.read().decode('utf-8')}")

                elif subor_typ == "application/pdf":
                    try:
                        pdf_reader = pypdf.PdfReader(uploaded_file)
                        pdf_text = "".join([page.extract_text() or "" for page in pdf_reader.pages])
                        parts_list.append(f"PDF ({nazov_suboru}):\n{pdf_text}")
                    except Exception as e:
                        st.error(f"PDF Chyba: {e}")

                elif nazov_suboru.endswith((".xlsx", ".xls", ".csv")):
                    try:
                        df = pd.read_csv(uploaded_file) if nazov_suboru.endswith(".csv") else pd.read_excel(uploaded_file)
                        parts_list.append(f"Tabuľka ({nazov_suboru}):\n{df.to_markdown(index=False)}")
                    except Exception as e:
                        st.error(f"Tabuľka Chyba: {e}")

            parts_list.append(prompt)
            aktualny_chat["messages"].append(sprava_pouzivatela)

            # Odozva z Google Gemini 2.5 API
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                
                with st.spinner("Generujem..."):
                    tools_list = []
                    if st.session_state.enable_web_search:
                        tools_list.append(types.Tool(google_search=types.GoogleSearch()))

                    config = types.GenerateContentConfig(
                        system_instruction=ROLY[st.session_state.vybrana_rola],
                        temperature=st.session_state.temperature,
                        max_output_tokens=st.session_state.max_tokens,
                        tools=tools_list
                    )

                    selected_model_id = MODELE[st.session_state.vybrany_model]

                    try:
                        response_stream = client.models.generate_content_stream(
                            model=selected_model_id,
                            contents=parts_list,
                            config=config
                        )

                        plny_text = ""
                        for chunk in response_stream:
                            if chunk.text:
                                plny_text += chunk.text
                                message_placeholder.markdown(plny_text + "▌")

                        message_placeholder.markdown(plny_text)
                        aktualny_chat["messages"].append({"role": "assistant", "content": plny_text})

                    except Exception as e:
                        message_placeholder.error(f"Chyba API: {e}")

            st.rerun()

# ==============================================================================
# END OF PUBLIC APPLICATION (NO LOGIN)
# ==============================================================================
