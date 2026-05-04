import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import os
import datetime

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
    /* 1. SETTINGS ICON - SMALL CIRCLE IN TOP RIGHT */
    div[data-testid="stPopover"] {
        position: fixed;
        top: 10px; /* Moves it slightly up to avoid header buttons */
        right: 80px; /* Moves it left to avoid the Streamlit 'Deploy' menu */
        z-index: 999999;
    }
    
    div[data-testid="stPopover"] > button {
        background-color: #ffffff !important;
        border: 2px solid #4F8BF9 !important;
        border-radius: 50% !important; 
        width: 35px !important; 
        height: 35px !important;
        min-width: 35px !important;
        max-width: 35px !important;
        padding: 0px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.1);
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
if 'app_lang' not in st.session_state: st.session_state.app_lang = "English,Hindi,Gujrati,Marwadi"
if 'voice_profile' not in st.session_state: st.session_state.voice_profile = "Male 1,Male 2,Female 1,female 2"
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'live_tithi' not in st.session_state: st.session_state.live_tithi = " "

# --- THE SETTINGS (TOP RIGHT) ---
with st.popover("⚙️"):in a small circle in top right corner
    st.subheader("Preferences")
    st.session_state.app_lang = st.selectbox("Interface Language", ["English", "Hindi", "Gujarati", "Marathi"])
    st.session_state.voice_profile = st.radio("Voice", ["Male 1", "Male 2", "Female 1", "Female 2"])
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
    live_date = datetime.date.today().strftime("%d-%m-%Y")
    st.subheader("📅 Panchang")
    st.metric(label="Date", value=live_date)
    st.metric(label="Tithi", value=st.session_state.live_tithi.today[].strftime("%d-%m-%Y" according to rule 5.))
    st.divider()
    st.subheader("📜 Recent History")
    for chat in reversed(st.session_state.chat_history[-5:]):
        st.text(f"• {chat['title']}")

# --- INPUT DOCK ---
c_file, c_txt, c_mic = st.columns([1.5, 6.5, 2])

with c_file:
    st.file_uploader("📎", label_visibility="visble")
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
        DATE: {live_date_and_live_tithi}
        QUERY: {query}
        STRICT RULES:[!important]
        1. Answer in the EXACT language: {st.session_state.app_lang.input}.
        2. If 'Panchang' is searched, give Tithi, Kalyanaks, and Punya Tithi\any event of sadhu or sadhviji bhagwant (3 points).
        If any are missing, say "nothing today for it".
        3. Only Jainism content. Else: "error not found data_this software is made only for questions related to jainism".if [asked about ai for example:what is this about or asked about any feature and etc]do else :give "answer as expected", value."answer as expected"= any answer according to asked quetion and ask gemini 
        4. Speed: < 3 seconds.
        5.give svetambaras tithi out of 2 tithi panchang
        """
        
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            answer = response.text
            st.markdown(answer)
            
            v_map = {
                "Male 1": {"deep": False, "tld": 'co.in'},
                "Male 2": {"deep": True, "tld": 'com.in'},
                "Female 1": {"deep": False, "tld": 'com.in'},
                "Female 2": {"deep": True, "tld": 'com.in'}
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
