import streamlit as st 
import google.generativeai as genai
from gtts import gTTS
import os
import datetime
import urllib.request
import urllib.error
import re
import json
from io import BytesIO
from PIL import Image

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="SamyakAI", page_icon="logo.png", layout="wide", initial_sidebar_state="expanded")

# --- DIRECTORY SETUP FOR DATA VAULT ---
VAULT_DIR = "jain_vault"
os.makedirs(VAULT_DIR, exist_ok=True)

# --- PANCHANG MULTI-YEAR DATA STORE ---
# Today's date set explicitly. Remaining space left open for image data entry extraction.
STATIC_PANCHANG = {
    "2026-08-28": "Shravan Sud 15",
    # ---> PASTE YOUR 2-YEAR EXTRACTED PANCHANG DATA HERE <---
}

# --- AUTOMATIC PANCHANG MANAGER ---
PANCHANG_VAULT_FILE = os.path.join(VAULT_DIR, "panchang_vault.json")

def fetch_tithi_from_stavan() -> str:
    url = "https://stavan.com/"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            match = re.search(r"([A-Za-z]+)\s+(Sud|Vad|Shukla|Krishna)\s+(\d{1,2})", html, re.IGNORECASE)
            if match:
                month = match.group(1).capitalize()
                phase = 'Sud' if match.group(2).capitalize() in ['Sud', 'Shukla'] else 'Vad'
                day = match.group(3)
                return f"{month} {phase} {day}"
    except Exception:
        pass
    return ""

def get_tithi() -> str:
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    # 1. Check if user uploaded a dynamic panchang json file
    if os.path.exists(PANCHANG_VAULT_FILE):
        try:
            with open(PANCHANG_VAULT_FILE, "r", encoding="utf-8") as f:
                uploaded_panchang = json.load(f)
                if today_str in uploaded_panchang:
                    return uploaded_panchang[today_str]
        except Exception:
            pass

    # 2. Check static panchang dictionary
    if today_str in STATIC_PANCHANG:
        return STATIC_PANCHANG[today_str]
        
    # 3. Fallback exclusively to stavan.com
    stavan_tithi = fetch_tithi_from_stavan()
    if stavan_tithi:
        return stavan_tithi

    return "Tithi Pending Update"

def is_jain_or_ai_query(query: str) -> bool:
    lower = query.lower()
    keywords = [
        "jain", "jainism", "panchang", "tithi", 
        "ai", "artificial intelligence", "gemini", "chatgpt", "machine learning"
    ]
    return any(word in lower for word in keywords)

# --- GEMINI SETUP ---
if "API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["API_KEY"])
else:
    st.error("API Key not found in Streamlit Secrets.")

MODEL_NAME = 'gemini-1.5-flash'

# --- UI MULTI-LANGUAGE DICTIONARY & CSS ---
ui_labels = {
    "English": {"hist": "Recent History", "pan": "Panchang", "ask": "Ask SamyakAI logic...", "upload": "Upload File / Image to Vault"},
    "Hindi": {"hist": "इतिहास", "pan": "पंचांग", "ask": "तर्क पूछें...", "upload": "वॉल्ट में फाइल जोड़ें"},
    "Gujarati": {"hist": "ઇતિહાસ", "pan": "પંચાંગ", "ask": "તર્ક પૂછો...", "upload": "વોલ્ટમાં ફાઇલ અપલોડ કરો"},
    "Marathi": {"hist": "इतिहास", "pan": "पंचांग", "ask": "तर्क विचारा...", "upload": "व्हॉल्टमध्ये फाइल टाका"}
}

st.markdown("""
    <style>
    /* SIDEBAR TOGGLE VISIBILITY */
    button[data-testid="stSidebarCollapseButton"] {
        visibility: visible !important;
        display: block !important;
    }
    @media (max-width: 768px) {
        .stSidebar {
            display: block !important;
            width: 270px !important;
        }
        .stColumns {
            flex-direction: column !important;
        }
    }
    header {visibility: visible;}
    .block-container { padding-top: 1rem; }
    .stFileUploader {
        margin-bottom: -20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALIZE SESSION STATE ---
if 'voice_profile' not in st.session_state: st.session_state.voice_profile = "Male 1"
if 'app_lang' not in st.session_state: st.session_state.app_lang = "English"
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'live_tithi' not in st.session_state: st.session_state.live_tithi = ""
if 'last_tithi_date' not in st.session_state: st.session_state.last_tithi_date = None

# --- UPDATE TITHI DAILY ---
today = datetime.date.today()
if st.session_state.last_tithi_date != today:
    st.session_state.live_tithi = get_tithi()
    st.session_state.last_tithi_date = today

labels = ui_labels.get(st.session_state.app_lang, ui_labels["English"])

# --- PERSISTENT SIDEBAR CONTROLS & NAVIGATION ---
with st.sidebar:
    st.title("Samyak Navigation")
    
    st.subheader("⚙️ Settings")
    st.session_state.app_lang = st.selectbox(
        "🌐 Language", 
        ["English", "Hindi", "Gujarati", "Marathi"],
        index=["English", "Hindi", "Gujarati", "Marathi"].index(st.session_state.app_lang)
    )
    st.session_state.voice_profile = st.radio(
        "🎙️ Voice Profile", 
        ["Male 1", "Male 2", "Female 1", "Female 2"],
        index=["Male 1", "Male 2", "Female 1", "Female 2"].index(st.session_state.voice_profile)
    )
    
    st.divider()
    
    live_date = datetime.date.today().strftime("%d-%m-%Y")
    st.subheader(f"📅 {labels['pan']}")
    st.metric(label="Date (English)", value=live_date)
    st.metric(label="Tithi", value=st.session_state.live_tithi or "Shravan Sud 15")
    
    st.divider()
    
    st.subheader(f"📜 {labels['hist']}")
    if st.session_state.chat_history:
        for chat in reversed(st.session_state.chat_history[-5:]):
            st.text(f"• {chat['title']}")
    else:
        st.text("No history yet.")

# --- TOP CENTRE LOGO & SIGNATURE ---
_, center_col, _ = st.columns([1, 2, 1])
with center_col:
    st.image("logo.png", use_container_width=True)
    st.markdown("<p style='text-align: center; font-size: 30px; font-weight: bold;'>Your Jain AI-Question Companion</p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: right; font-size: 24px; color: #888;'>- MADE BY STAVYA SHAH</p>", unsafe_allow_html=True)

st.write("---")

# --- INPUT DOCK ---
c_file, c_txt, c_mic = st.columns([2, 6, 2])

image_input = None
with c_file:
    uploaded_file = st.file_uploader("📎", label_visibility="visible", type=["png", "jpg", "jpeg", "txt", "json"])
    st.caption("Vault: 10GB Max")
    if uploaded_file is not None:
        file_path = os.path.join(VAULT_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        if uploaded_file.name.endswith(".json"):
            with open(PANCHANG_VAULT_FILE, "wb") as pf:
                pf.write(uploaded_file.getbuffer())
            st.success("Integrated new Panchang JSON dataset!")
            st.session_state.live_tithi = get_tithi()
        else:
            st.success(f"Absorbed to Vault: {uploaded_file.name}")

        if uploaded_file.type.startswith("image/"):
            image_input = Image.open(uploaded_file)

with c_txt:
    user_input = st.chat_input(labels["ask"])

with c_mic:
    audio_data = st.audio_input("🎤", label_visibility="visible", key="single_mic_input")

# --- PROCESSING ---
if user_input or audio_data or image_input:
    query = user_input if user_input else ("Voice prompt question" if audio_data else "Image analysis query")
    
    with st.chat_message("assistant"):
        prompt = f"""
        DATE: {live_date} (English format)
        CURRENT TITHI: {st.session_state.live_tithi or 'Shravan Sud 15'}
        QUERY: {query}
        STRICT RULES:[!important]
        1. Answer in the EXACT language: {st.session_state.app_lang}.
        2. Use exact month Sud/Vad day numbering for tithi, like Vaishakh Sud 11.
        3. Mention kalyanak of any god if it falls on the same day.
        4. Mention punya tithi / special day about any sadhu/sadhviji/bhagwant if it falls on the same day.
        5. Only Jainism or AI content is valid. If the question is not about Jainism or AI, answer in red text: "This software is made only for questions related to Jainism or AI".
        6. Speed: < 3 seconds.
        7. Provide tithi information when relevant.
        """
        
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            
            if image_input:
                response = model.generate_content([prompt, image_input])
            else:
                response = model.generate_content(prompt)
                
            answer = response.text
            
            if is_jain_or_ai_query(query):
                st.markdown(answer)
            else:
                st.markdown(f"<div style='color:red'>{answer}</div>", unsafe_allow_html=True)
            
            v_map = {
                "Male 1": {"slow": False, "tld": 'co.in'},
                "Male 2": {"slow": True, "tld": 'co.in'},
                "Female 1": {"slow": False, "tld": 'com'},
                "Female 2": {"slow": True, "tld": 'com'}
            }
            cfg = v_map.get(st.session_state.voice_profile, {"slow": False, "tld": 'co.in'})
            l_code = 'hi' if any(ord(c) > 128 for c in answer[:15]) else 'en'
            
            audio_buffer = BytesIO()
            tts = gTTS(text=answer, lang=l_code, slow=cfg["slow"], tld=cfg["tld"])
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            st.audio(audio_buffer, format="audio/mp3", autoplay=True)
            st.session_state.chat_history.append({"title": query})
                
        except Exception as e:
            st.error(f"Processing error: {str(e)}")
