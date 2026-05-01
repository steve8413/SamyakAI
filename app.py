import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import os
import datetime

# --- PILLAR 1: THE BRAIN ---
# We pull the key from the hidden Streamlit Secrets vault instead
genai.configure(api_key=st.secrets["API_KEY"])
MODEL_NAME = 'gemini-3.1-flash-lite-preview'

# --- UI & CSS (THE OVERRIDE) ---
# We force the sidebar to be "expanded" and stay that way.
st.set_page_config(page_title="SamyakAI", page_icon="logo.png", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* 1. FORCE SETTINGS ICON VISIBILITY */
    /* We create a high-visibility floating container for the popover */
    div[data-testid="stPopover"] {
        position: fixed;
        top: 15px;
        right: 15px;
        z-index: 999999;
        background-color: #ffffff;
        border-radius: 50%;
        border: 2px solid #4F8BF9;
    }

    /* 2. PERSISTENT SIDEBAR - REMOVE TOGGLE BUTTON */
    button[data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }
    
    /* 3. CLEAN UP INTERFACE */
    header {visibility: visible;}
    .block-container { padding-top: 0rem; }
    
    /* 4. FIX UPLOAD SECTION APPEARANCE */
    .stFileUploader {
        margin-bottom: -20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALIZE DATA ---
if 'app_lang' not in st.session_state: st.session_state.app_lang = "English"
if 'voice_profile' not in st.session_state: st.session_state.voice_profile = "Female 1"
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
# Start with a real Tithi so it's never empty
if 'live_tithi' not in st.session_state: st.session_state.live_tithi = "Vaishakh Sud 11"

# --- THE SETTINGS (TOP RIGHT) ---
with st.popover("⚙️"):
    st.subheader("Preferences")
    st.session_state.app_lang = st.selectbox("Interface Language", ["English", "Hindi", "Gujarati", "Marathi"])
    st.session_state.voice_profile = st.radio("Voice", ["Male 1", "Male 2", "Female 1", "Female 2"])
    st.info("📁 Vault Capacity: 10GB Active")

# --- TOP CENTRE LOGO & SIGNATURE ---
# Using columns to keep it tight and centered
_, center_col, _ = st.columns([1, 2, 1])
with center_col:
    try:
        st.image("logo.png", use_container_width=True)
        # We only use the caption lines to avoid extra titles
        st.markdown("<p style='text-align: center; font-size: 30px; font-weight: bold;'>Your Jain AI-Question Companion</p>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: right; font-size: 24px; color: #888;'>- MADE BY STAVYA SHAH</p>", unsafe_allow_html=True)
    except: 
        st.write("### SamyakAI")

st.write("---")

# --- THE PERSISTENT SIDEBAR ---
with st.sidebar:
    st.title("Samyak Navigation")
    
    # Live updating Panchang
    live_date = datetime.date.today().strftime("%d-%m-%Y")
    st.subheader("📅 Panchang")
    st.metric(label="Date", value=live_date)
    st.metric(label="Tithi", value=st.session_state.live_tithi)
    
    st.divider()
    
    st.subheader("📜 Recent History")
    for chat in reversed(st.session_state.chat_history[-5:]):
        st.text(f"• {chat['title']}")

# --- INPUT DOCK ---
# Arranging Upload, Chat, and Mic in one row
c_file, c_txt, c_mic = st.columns([1.5, 6.5, 2])

with c_file:
    # Note: To see "10GB" here, you MUST run: 
    # streamlit run your_file.py --server.maxUploadSize 10240
    st.file_uploader("📎", label_visibility="collapsed")
    st.caption("Vault: 10GB Max")

with c_txt:
    user_input = st.chat_input("Ask a question...")

with c_mic:
    # Adding a unique key based on time to ensure the mic "wakes up"
    mic_key = f"mic_{datetime.datetime.now().strftime('%M%S')}"
    audio_data = st.audio_input("🎤", label_visibility="collapsed", key=mic_key)

# --- PROCESSING ---
if user_input or audio_data:
    query = user_input if user_input else "Voice prompt"
    
    with st.chat_message("assistant"):
        # The Brain: Instructions for language, panchang, and speed
        prompt = f"""
        DATE: {live_date}
        QUERY: {query}
        RULES:
        1. Answer in the EXACT language of the query (English, Hindi, Gujarati, or Marathi).
        2. If 'Panchang' is searched, give Tithi, Kalyanaks, and Punya Tithi (3 points).
        3. Only Jainism content. Else: "error not found data and this software is made only for questions related to jainism".
        4. Speed: < 3 seconds.
        """
        
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            answer = response.text
            st.markdown(answer)
            
            # Voice Mapping (Male/Female 1 & 2)
            v_map = {
                "Male 1": {"slow": False, "tld": 'co.uk'},
                "Male 2": {"slow": True, "tld": 'com.au'},
                "Female 1": {"slow": False, "tld": 'com'},
                "Female 2": {"slow": True, "tld": 'ie'}
            }
            cfg = v_map[st.session_state.voice_profile]
            # Simple check for Hindi/Gujarati/Marathi characters to set TTS language
            l_code = 'hi' if any(ord(c) > 128 for c in answer[:15]) else 'en'
            
            tts = gTTS(text=answer, lang=l_code, slow=cfg["slow"])
            tts.save("voice_reply.mp3")
            st.audio("voice_reply.mp3", autoplay=True)
            
            # Updates
            st.session_state.chat_history.append({"title": query})
            if "Tithi:" in answer:
                st.session_state.live_tithi = answer.split("Tithi:")[1].split("\n")[0].strip()
                st.rerun()
                
        except Exception as e:
            st.error("Engine reset. Please try again.")
