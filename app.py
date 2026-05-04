import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import os
import datetime
import urllib.request
import urllib.error
import re
# --- JAIN CALENDAR HELPER ---
def fetch_svetambara_tithi_from_url(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except (urllib.error.URLError, Exception):
        return ""

    patterns = [
        r"\b([A-Za-z]+)\s+(Sud|Vad|sud|vad)\s+(\d{1,2})\b",
        r"\bTithi[:\s]+([A-Za-z]+)\s+(Sud|Vad)\s+(\d{1,2})\b",
    ]
    for pat in patterns:
        match = re.search(pat, html, re.IGNORECASE)
        if match:
            month = match.group(1).capitalize()
            phase = match.group(2).capitalize()
            number = match.group(3)
            return f"{month} {phase} {number}"

    return ""


def get_svetambara_tithi() -> str:
    today = datetime.date.today()
    candidate_urls = []
    if "JAIN_TITHI_URL" in st.secrets:
        candidate_urls.append(st.secrets["JAIN_TITHI_URL"])

    candidate_urls.extend([
        "https://www.jainpanchang.com/panchang/",
        "https://www.jainpanchang.com/",
        "https://jainpanchang.com/",
    ])

    for url in candidate_urls:
        tithi = fetch_svetambara_tithi_from_url(url)
        if tithi:
            return tithi

    return f"Tithi not found for {today.strftime('%d-%m-%Y')} (configure JAIN_TITHI_URL in Streamlit secrets)"


def is_jain_or_ai_query(query: str) -> bool:
    lower = query.lower()
    keywords = [
        "jain",
        "jainism",
        "svetambara",
        "panchang",
        "tithi",
        "ai",
        "artificial intelligence",
        "gemini",
        "chatgpt",
        "machine learning"
    ]
    return any(word in lower for word in keywords)

# --- PILLAR 1: THE BRAIN ---
if "API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["API_KEY"])
else:
    st.error("API Key not found in Streamlit Secrets.")

MODEL_NAME = 'gemini-3.1-flash-lite-preview'

# --- UI & CSS (THE OVERRIDE) ---
st.set_page_config(page_title="SamyakAI", page_icon="logo.png", layout="wide", initial_sidebar_state="expanded")
# UI Multi-language Dictionary
ui_labels = {
    "English": {"hist": "1. History", "pan": "2. Panchang", "ask": "Ask SamyakAI logic..."},
    "Hindi": {"hist": "1. इतिहास", "pan": "2. पंचांग", "ask": "तर्क पूछें..."},
    "Gujarati": {"hist": "1. ઇતિહાસ", "pan": "2. પંચાંગ", "ask": "તર્ક પૂછો..."},
    "Marathi": {"hist": "1. इतिहास", "pan": "2. पंचांग", "ask": "तर्क विचारा..."}
}

st.markdown("""
    <style>
    /* 1. SETTINGS ICON - FLOATING CIRCLE IN TOP RIGHT CORNER */
    div[data-testid="stPopover"] {
        position: fixed !important;
        top: 20px !important;
        right: 20px !important;
        z-index: 999999 !important;
    }
    
    div[data-testid="stPopover"] > button {
        background-color: #4F8BF9 !important;
        border: none !important;
        border-radius: 50% !important; 
        width: 50px !important; 
        height: 50px !important;
        min-width: 50px !important;
        max-width: 50px !important;
        padding: 0px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0px 4px 12px rgba(79, 139, 249, 0.4);
        font-size: 24px !important;
    }
    
    div[data-testid="stPopover"] > button:hover {
        background-color: #3f7fe0 !important;
        box-shadow: 0px 6px 16px rgba(79, 139, 249, 0.6) !important;
    }
    
    div[data-testid="stPopover"] > button div {
        padding: 0px !important;
        margin: 0px !important;
    }

    /* 2. SIDEBAR TOGGLE VISIBILITY */
    button[data-testid="stSidebarCollapseButton"] {
        visibility: visible !important;
        display: block !important;
    }
    
    /* 3. CLEAN UP INTERFACE */
    header {visibility: visible;}
    .block-container { padding-top: 1rem; }
    
    /* 4. FIX UPLOAD SECTION APPEARANCE */
    .stFileUploader {
        margin-bottom: -20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALIZE DATA ---
if 'voice_profile' not in st.session_state:
    st.session_state.voice_profile = st.radio("Voice", ["Male 1", "Male 2", "Female 1", "Female 2"])
# ^ This gap must be consistent (4 spaces)
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'live_tithi' not in st.session_state: st.session_state.live_tithi = ""
if 'last_tithi_date' not in st.session_state: st.session_state.last_tithi_date = None

# --- UPDATE TITHI DAILY ---
today = datetime.date.today()
if st.session_state.last_tithi_date != today:
    st.session_state.live_tithi = get_svetambara_tithi()
    st.session_state.last_tithi_date = today

# --- THE SETTINGS (TOP RIGHT) ---
with st.popover("⚙️"):
    st.subheader("Preferences")
    st.session_state.app_lang = st.selectbox("Interface Language", ["English", "Hindi", "Gujarati", "Marathi"])
    st.session_state.voice_profile = st.radio("Voice", ["Male 1", "Male 2", "Female 1", "Female 2"]),lang='st.session_state.app_lang = "English,Hindi,Gujrati,Marwadi"'
    st.info("📁 Vault Capacity: 10GB Active")

# --- TOP CENTRE LOGO & SIGNATURE ---
_, center_col, _ = st.columns([1, 2, 1])
with center_col:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown("<h1 style='text-align: center; color: #4F8BF9;'>SamyakAI</h1>", unsafe_allow_html=True)
        
    st.markdown("<p style='text-align: center; font-size: 30px; font-weight: bold;'>Your Jain AI-Question Companion</p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: right; font-size: 24px; color: #888;'>- MADE BY STAVYA SHAH</p>", unsafe_allow_html=True)

st.write("---")

# --- THE PERSISTENT SIDEBAR ---
with st.sidebar:
    st.title("Samyak Navigation")
    live_date = datetime.date.today().strftime("%d-%m-%Y")  # English date format
    st.subheader("📅 Panchang")
    st.metric(label="Date (English)", value=live_date)
    st.metric(label="Svetambara Tithi", value=st.session_state.live_tithi)
    st.divider()
    st.subheader("📜 Recent History")
    for chat in reversed(st.session_state.chat_history[-5:]):
        st.text(f"• {chat['title']}")

# --- INPUT DOCK ---
c_file, c_txt, c_mic = st.columns([1.5, 6.5, 2])

with c_file:
    st.file_uploader("📎", label_visibility="visible")
    st.caption("Vault: 10GB Max")

with c_txt:
    user_input = st.chat_input("Ask a question...")

with c_mic:
    mic_key = f"mic_{datetime.datetime.now().strftime('%M%S')}"
    audio_data = st.audio_input("🎤", label_visibility="visible", key=mic_key)

# --- PROCESSING ---
if user_input or audio_data:
    query = user_input if user_input else "Voice prompt"
    
    with st.chat_message("assistant"):
        prompt = f"""
        DATE: {live_date} (English format)
        CURRENT SVETAMBARA TITHI: {st.session_state.live_tithi}  # strict month Sud/Vad day format
        QUERY: {query}
        STRICT RULES:[!important]
        1. Answer in the EXACT language: {st.session_state.app_lang}.
        2. If 'News' is searched, pointUse exact month Sud/Vad day numbering like Shukravar,Vaishakh Sud 11 ,2082 or Shukravar,Vaishakh Vad 11, 2082. + 2. kalyanak of any god should be mentioned if it falls on the same day. Do not use any other format for tithi. If tithi is not found, say "Tithi not found " + 3. punya tithi /special day about any sadhu /sadhviji bhagwant should also be mentioned if it falls on the same day. ask to gemini, If tithi is not found, say "Tithi not found".
        3. Only Jainism or AI content is valid. If the question is not about Jainism or AI, answer in red text and say: "error not found data_this software is made only for questions related to Jainism or AI".
        4. Speed: < 3 seconds.
        5. Give Svetambara tithi out of 2 tithi panchang.
        """
        
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            answer = response.text
            if is_jain_or_ai_query(query):
                st.markdown(answer)
            else:
                st.markdown(f"<div style='color:red'>{answer}</div>", unsafe_allow_html=True)
            
            v_map = {
                "Male 1": {"slow": False, "tld": 'co.in'},
                "Male 2": {"slow": True, "tld": 'com.in'},
                "Female 1": {"slow": False, "tld": 'com.in'},
                "Female 2": {"slow": True, "tld": 'com.in'}
            }
            cfg = v_map[st.session_state.voice_profile]
            l_code = 'hi' if any(ord(c) > 128 for c in answer[:15]) else 'en'
            
            tts = gTTS(text=answer, lang=l_code, slow=cfg["slow"])
            tts.save("voice_reply.mp3")
            st.audio("voice_reply.mp3", autoplay=True)
            
            st.session_state.chat_history.append({"title": query})
            if "Tithi:" in answer:
                st.session_state.live_tithi = answer.split("Tithi:")[1].split("\n")[0].strip()
                st.rerun()
                
        except Exception as e:
            st.error("Engine reset. Please try again.")
