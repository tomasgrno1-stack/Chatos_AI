import streamlit as st
import google.generativeai as genai
from PIL import Image
import uuid
import pypdf
import docx
import pandas as pd
import requests

# 1. Nastavenie stránky
st.set_page_config(
    page_title="Polaris",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="expanded"
)

# 2. Rýchla detekcia jazyka s krátkym timeoutom (max 1 sekunda)
@st.cache_data(ttl=86400)
def ziskaj_jazyk_pouzivatela():
    try:
        response = requests.get("https://ipapi.co/json/", timeout=1)
        data = response.json()
        krajina = data.get("country_code", "US")
        
        jazyky = {
            "SK": "sk", "CZ": "cs", "DE": "de", 
            "AT": "de", "PL": "pl", "ES": "es", 
            "FR": "fr", "IT": "it"
        }
        return jazyky.get(krajina, "en")
    except Exception:
        return "en"

jazyk_ui = ziskaj_jazyk_pouzivatela()

# Slovník lokalizácie rozhrania
TEXTY = {
    "sk": {
        "title": '<span class="rgb-star">★</span> Polaris <span class="rgb-star">★</span>',
        "subtitle": "Autor: Tomáš Grňo",
        "new_chat": "➕ Nový",
        "clear_all": "🧹 Všetko",
        "history": "💬 História chatov",
        "settings": "⚙️ Nastavenia",
        "placeholder": "Ako ti môžem pomôcť?",
        "hero_title": 'Ahoj, ja som Polaris <span class="rgb-star">★</span>',
        "hero_sub": "S čím chceš dnes začať?",
        "card1_title": "💡 Navrhni nápad na projekt",
        "card1_sub": "Aplikácia alebo biznis nápad",
        "card1_prompt": "Navrhni mi 3 kreatívne nápady na softvérový projekt.",
        "card2_title": "📝 Napíš e-mail / správu",
        "card2_sub": "Profesionálna komunikácia",
        "card2_prompt": "Pomôž mi napísať profesionálny e-mail s poďakovaním.",
        "role_label": "Rola Polaris:",
        "thinking": "Polaris premýšľa..."
    },
    "cs": {
        "title": '<span class="rgb-star">★</span> Polaris <span class="rgb-star">★</span>',
        "subtitle": "Autor: Tomáš Grňo",
        "new_chat": "➕ Nový",
        "clear_all": "🧹 Vše",
        "history": "💬 Historie chatů",
        "settings": "⚙️ Nastavení",
        "placeholder": "Jak vám mohu pomoci?",
        "hero_title": 'Ahoj, já jsem Polaris <span class="rgb-star">★</span>',
        "hero_sub": "Čím dnes začneme?",
        "card1_title": "💡 Navrhni nápad na projekt",
        "card1_sub": "Aplikace nebo podnikatelský nápad",
        "card1_prompt": "Navrhni mi 3 kreativní nápady na softwarový projekt.",
        "card2_title": "📝 Napiš e-mail / zpráva",
        "card2_sub": "Profesionální komunikace",
        "card2_prompt": "Pomoz mi napsat profesionální e-mail s poděkováním.",
        "role_label": "Role Polaris:",
        "thinking": "Polaris přemýšlí..."
    },
    "de": {
        "title": '<span class="rgb-star">★</span> Polaris <span class="rgb-star">★</span>',
        "subtitle": "Autor: Tomáš Grňo",
        "new_chat": "➕ Neu",
        "clear_all": "🧹 Alles löschen",
        "history": "💬 Chat-Verlauf",
        "settings": "⚙️ Einstellungen",
        "placeholder": "Wie kann ich dir helfen?",
        "hero_title": 'Hallo, ich bin Polaris <span class="rgb-star">★</span>',
        "hero_sub": "Womit möchtest du heute beginnen?",
        "card1_title": "💡 Schlage eine Projektidee vor",
        "card1_sub": "App- oder Geschäftsidee",
        "card1_prompt": "Schlage mir 3 kreative Ideen für ein Softwareprojekt vor.",
        "card2_title": "📝 Schreibe eine E-Mail / Nachricht",
        "card2_sub": "Professionelle Kommunikation",
        "card2_prompt": "Hilf mir, eine professionelle Dankes-E-Mail zu schreiben.",
        "role_label": "Rolle von Polaris:",
        "thinking": "Polaris denkt nach..."
    },
    "en": {
        "title": '<span class="rgb-star">★</span> Polaris <span class="rgb-star">★</span>',
        "subtitle": "Created by: Tomáš Grňo",
        "new_chat": "➕ New",
        "clear_all": "🧹 Clear all",
        "history": "💬 Chat History",
        "settings": "⚙️ Settings",
        "placeholder": "How can I help you?",
        "hero_title": 'Hello, I am Polaris <span class="rgb-star">★</span>',
        "hero_sub": "What would you like to start with today?",
        "card1_title": "💡 Suggest a project idea",
        "card1_sub": "App or business idea",
        "card1_prompt": "Suggest 3 creative ideas for a software project.",
        "card2_title": "📝 Write an email / message",
        "card2_sub": "Professional communication",
        "card2_prompt": "Help me write a professional thank-you email.",
        "role_label": "Polaris Role:",
        "thinking": "Polaris is thinking..."
    }
}

t = TEXTY.get(jazyk_ui, TEXTY["en"])

# 3. CSS Štýlovanie + RGB Efekt na hviezdy
st.markdown("""
    <style>
    /* RGB Animácia pre hviezdy */
    @keyframes rgbGlow {
        0% { color: #ff0055; text-shadow: 0 0 8px #ff0055; }
        20% { color: #00e5ff; text-shadow: 0 0 8px #00e5ff; }
        40% { color: #00ff66; text-shadow: 0 0 8px #00ff66; }
        60% { color: #ffcc00; text-shadow: 0 0 8px #ffcc00; }
        80% { color: #b026ff; text-shadow: 0 0 8px #b026ff; }
        100% { color: #ff0055; text-shadow: 0 0 8px #ff0055; }
    }

    .rgb-star {
        display: inline-block;
        animation: rgbGlow 3s infinite linear;
        font-weight: bold;
    }

    .stApp {
        background: radial-gradient(ellipse at bottom, #1b2735 0%, #090a0f 100%);
        background-attachment: fixed;
        color: #e6edf3;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    .stApp::before {
        content: "";
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(circle at 50% 30%, rgba(76, 29, 149, 0.25) 0%, rgba(15, 23, 42, 0) 70%),
                    radial-gradient(circle at 80% 80%, rgba(14, 165, 233, 0.15) 0%, rgba(15, 23, 42, 0) 50%);
        pointer-events: none;
        z-index: 0;
    }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: rgba(15, 23, 42, 0.6); }
    ::-webkit-scrollbar-thumb { background: rgba(56, 189, 248, 0.2); border-radius: 10px; }

    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.85) !important;
        backdrop-filter: blur(12px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    [data-testid="stSidebar"] .stButton > button {
        background: rgba(30, 41, 59, 0.4) !important;
        backdrop-filter: blur(6px);
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    [data-testid="stChatMessage"] {
        background-color: transparent !important;
        border: none !important;
        padding: 0.5rem 0;
        margin-bottom: 0.8rem;
        animation: fadeIn 0.3s ease-out forwards;
    }

    [data-testid="stChatMessageAvatarUser"] {
        background: linear-gradient(135deg, #6366f1, #a855f7) !important;
        border-radius: 50% !important;
    }

    [data-testid="stChatMessageAvatarAssistant"] {
        background: linear-gradient(135deg, #0ea5e9, #a855f7) !important;
        border-radius: 50% !important;
    }

    [data-testid="stChatInput"] {
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        background-color: rgba(15, 23, 42, 0.9) !important;
    }

    div[data-testid="stBottom"], div[data-testid="stBottom"] > div {
        background: transparent !important;
        border: none !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.stPopover) {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        width: calc(100% - 40px);
        max-width: 730px;
        z-index: 100;
        background-color: #0f172a;
        padding: 6px 12px;
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .stPopover>button {
        border-radius: 50% !important;
        width: 42px !important;
        height: 42px !important;
        padding: 0 !important;
        font-size: 20px !important;
        background-color: rgba(30, 41, 59, 0.8) !important;
    }

    .main .block-container { padding-bottom: 120px; }
    </style>
""", unsafe_allow_html=True)

# 4. Načítanie API kľúča
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Chýba GOOGLE_API_KEY v Secrets!")
    st.stop()

# 5. Výber najpokročilejších modelov pre hlbokú inteligenciu
@st.cache_data(ttl=86400)
def ziskaj_dostupne_modely():
    return [
        "gemini-1.5-flash",        # Ultra-rýchla moderná záloha
        "gemini-3.6-flash"         # Štandardná záloha
    ]

# 6. Správa session state
if "chats" not in st.session_state:
    st.session_state.chats = {}

if "current_chat_id" not in st.session_state:
    prve_id = str(uuid.uuid4())
    st.session_state.chats[prve_id] = {"title": "Polaris", "messages": []}
    st.session_state.current_chat_id = prve_id

if "aktivny_rezim" not in st.session_state:
    st.session_state.aktivny_rezim = "Standard"

def vytvor_novy_chat():
    nove_id = str(uuid.uuid4())
    st.session_state.chats[nove_id] = {"title": "Polaris", "messages": []}
    st.session_state.current_chat_id = nove_id

# 7. Pokročilé roly pre analytické uvažovanie
ROLY = {
    "Personal Assistant": """You are Polaris, a highly intelligent, expert AI assistant. 
ALWAYS respond in the EXACT same language that the user uses to write to you (e.g., if the user writes in Slovak, respond in Slovak; if in English, respond in English, etc.). 
Analyze requests deeply, think step-by-step when solving complex problems, and provide thorough, logically structured, and extremely helpful answers.""",
    
    "Programmer": """You are Polaris, an elite senior software engineer and system architect. 
ALWAYS respond in the EXACT same language used by the user. 
Provide clean, efficient, production-ready code with concise explanations and structural best practices.""",
    
    "English Teacher": "You are Polaris. Respond in English and provide a brief translation in the language used by the user below.",
    
    "Concise Assistant": "You are Polaris. ALWAYS respond in the EXACT same language used by the user, limiting responses to a maximum of 2-3 short sentences."
}

# 8. Bočný panel
with st.sidebar:
    st.markdown(f"## {t['title']}", unsafe_allow_html=True)
    
    col_new, col_clear = st.columns([0.7, 0.3])
    with col_new:
        if st.button(t["new_chat"], use_container_width=True):
            vytvor_novy_chat()
            st.rerun()
    with col_clear:
        if st.button(t["clear_all"], use_container_width=True):
            st.session_state.chats = {}
            vytvor_novy_chat()
            st.rerun()

    st.divider()
    st.subheader(t["history"])
    
    for chat_id, chat_data in list(st.session_state.chats.items()):
        is_active = (chat_id == st.session_state.current_chat_id)
        label = f"📍 {chat_data['title']}" if is_active else chat_data['title']
        
        col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
        with col1:
            if st.button(label, key=f"select_{chat_id}", use_container_width=True):
                st.session_state.current_chat_id = chat_id
                st.rerun()
        with col2:
            if st.button("✏️", key=f"edit_btn_{chat_id}"):
                st.session_state[f"editing_{chat_id}"] = not st.session_state.get(f"editing_{chat_id}", False)
                st.rerun()
        with col3:
            if st.button("🗑", key=f"del_{chat_id}"):
                del st.session_state.chats[chat_id]
                if st.session_state.current_chat_id == chat_id:
                    if st.session_state.chats:
                        st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]
                    else:
                        vytvor_novy_chat()
                st.rerun()

        if st.session_state.get(f"editing_{chat_id}", False):
            novy_nazov = st.text_input("Name:", value=chat_data['title'], key=f"rename_input_{chat_id}")
            if st.button("Save", key=f"save_rename_{chat_id}", use_container_width=True):
                if novy_nazov.strip():
                    st.session_state.chats[chat_id]['title'] = novy_nazov.strip()
                    st.session_state[f"editing_{chat_id}"] = False
                    st.rerun()

    st.divider()
    st.header(t["settings"])
    vybrana_rola = st.selectbox(t["role_label"], list(ROLY.keys()))

# 9. Hlavné okno chatu
aktualny_chat = st.session_state.chats[st.session_state.current_chat_id]

st.markdown(f"# {t['title']}", unsafe_allow_html=True)
st.caption(f"{t['subtitle']} | Mode: {st.session_state.aktivny_rezim}")

if len(aktualny_chat["messages"]) == 0:
    st.markdown(f"""
        <div style="text-align: center; padding: 30px 20px 20px 20px;">
            <h2 style="background: linear-gradient(to right, #38bdf8, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.2rem; font-weight: 700;">
                {t['hero_title']}
            </h2>
            <p style="color: #94a3b8; font-size: 1.05rem;">{t['hero_sub']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    col_card1, col_card2 = st.columns(2)
    with col_card1:
        if st.button(f"**{t['card1_title']}**\n\n_{t['card1_sub']}_", use_container_width=True):
            st.session_state["pouzity_prompt"] = t['card1_prompt']
            st.rerun()
    with col_card2:
        if st.button(f"**{t['card2_title']}**\n\n_{t['card2_sub']}_", use_container_width=True):
            st.session_state["pouzity_prompt"] = t['card2_prompt']
            st.rerun()

for idx, msg in enumerate(aktualny_chat["messages"]):
    avatar = "✨" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        if "image" in msg and msg["image"] is not None:
            st.image(msg["image"], use_container_width=True)
        
        if "file_info" in msg and msg["file_info"]:
            st.caption(f"📎 **{msg['file_info']}**")
            
        st.markdown(msg["content"])
        
        if msg["role"] == "assistant":
            with st.popover("📋"):
                st.code(msg["content"], language=None)

# 10. Spodný vstupný panel
col_plus, col_input = st.columns([0.1, 0.9])

with col_plus:
    with st.popover("➕"):
        nahraty_subor = st.file_uploader(
            "File:",
            type=["png", "jpg", "jpeg", "txt", "pdf", "docx", "xlsx", "xls", "csv"]
        )

with col_input:
    prompt_input = st.chat_input(t["placeholder"])

prompt = prompt_input or st.session_state.pop("pouzity_prompt", None)

# 11. Generovanie odpovede
if prompt:
    if len(aktualny_chat["messages"]) == 0:
        aktualny_chat["title"] = prompt[:18] + "..." if len(prompt) > 18 else prompt

    sprava_pouzivatela = {"role": "user", "content": prompt}
    obsah_spravy = [prompt]
    
    if 'nahraty_subor' in locals() and nahraty_subor is not None:
        subor_typ = nahraty_subor.type
        nazov_suboru = nahraty_subor.name
        
        if subor_typ in ["image/png", "image/jpeg", "image/jpg"]:
            img = Image.open(nahraty_subor)
            obsah_spravy.append(img)
            sprava_pouzivatela["image"] = img
            sprava_pouzivatela["file_info"] = nazov_suboru
            
        elif subor_typ == "text/plain":
            text_suboru = nahraty_subor.read().decode("utf-8")
            obsah_spravy.append(f"\n\nFile text ({nazov_suboru}):\n{text_suboru}")
            sprava_pouzivatela["file_info"] = nazov_suboru
            
        elif subor_typ == "application/pdf":
            try:
                pdf_reader = pypdf.PdfReader(nahraty_subor)
                pdf_text = "".join([page.extract_text() or "" for page in pdf_reader.pages])
                obsah_spravy.append(f"\n\nPDF content ({nazov_suboru}):\n{pdf_text}")
                sprava_pouzivatela["file_info"] = nazov_suboru
            except Exception as e:
                st.error(f"Error PDF: {e}")

        elif nazov_suboru.endswith(".docx"):
            try:
                doc = docx.Document(nahraty_subor)
                docx_text = "\n".join([p.text for p in doc.paragraphs if p.text])
                obsah_spravy.append(f"\n\nWord content ({nazov_suboru}):\n{docx_text}")
                sprava_pouzivatela["file_info"] = nazov_suboru
            except Exception as e:
                st.error(f"Error Word: {e}")

        elif nazov_suboru.endswith((".xlsx", ".xls", ".csv")):
            try:
                df = pd.read_csv(nahraty_subor) if nazov_suboru.endswith(".csv") else pd.read_excel(nahraty_subor)
                excel_text = df.to_markdown(index=False)
                obsah_spravy.append(f"\n\nTable data ({nazov_suboru}):\n{excel_text}")
                sprava_pouzivatela["file_info"] = nazov_suboru
            except Exception as e:
                st.error(f"Error Table: {e}")

    aktualny_chat["messages"].append(sprava_pouzivatela)
    
    with st.chat_message("user", avatar="👤"):
        if "image" in sprava_pouzivatela:
            st.image(sprava_pouzivatela["image"], use_container_width=True)
        if "file_info" in sprava_pouzivatela:
            st.caption(f"📎 **{sprava_pouzivatela['file_info']}**")
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="✨"):
        message_placeholder = st.empty()

        with st.spinner(t["thinking"]):
            # Optimalizácia parametrov pre hlboké uvažovanie bez umelých obmedzení
            generation_config = genai.types.GenerationConfig(
                temperature=0.7,
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192
            )

            # Rozšírený kontext (posledných 10 správ namiesto 4)
            pouzita_historia = aktualny_chat["messages"][:-1][-10:]
            
            gemini_history = []
            for m in pouzita_historia:
                role = "user" if m["role"] == "user" else "model"
                gemini_history.append({"role": role, "parts": [m["content"]]})

            dostupne_modely = ziskaj_dostupne_modely()
            
            posledna_chyba = ""
            uspesne = False
            
            for nazov_modelu in dostupne_modely:
                try:
                    model = genai.GenerativeModel(
                        model_name=nazov_modelu,
                        system_instruction=ROLY[vybrana_rola],
                        generation_config=generation_config
                    )
                    
                    chat = model.start_chat(history=gemini_history)
                    response = chat.send_message(obsah_spravy, stream=True)
                    
                    plny_text = ""
                    for chunk in response:
                        plny_text += chunk.text
                        message_placeholder.markdown(plny_text + "▌")
                    
                    message_placeholder.markdown(plny_text)
                    aktualny_chat["messages"].append({"role": "assistant", "content": plny_text})
                    uspesne = True
                    break
                except Exception as e:
                    posledna_chyba = str(e)
                    continue

            if not uspesne:
                message_placeholder.error(f"Error: {posledna_chyba}")
