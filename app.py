import os
import io
import time
import json
import re
import datetime
import urllib.request
import urllib.parse
import streamlit as st
from PIL import Image
from gtts import gTTS
from google import genai
from google.genai import types

# ------------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & VAULT SETUP
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="SamyakAI Studio",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

PANCHANG_VAULT_FILE = "panchang_vault.json"

# ------------------------------------------------------------------------------
# 2. GOOGLE GENAI CLIENT SETUP
# ------------------------------------------------------------------------------
api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("API_KEY")
if not api_key:
    st.error("🔑 GEMINI_API_KEY not found! Set it in your environment variables or Streamlit secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

# ------------------------------------------------------------------------------
# 3. PANCHANG & SYSTEM HELPERS
# ------------------------------------------------------------------------------
STATIC_PANCHANG = {
    "2026-08-28": "Shravan Sud 15"
}

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
    if os.path.exists(PANCHANG_VAULT_FILE):
        try:
            with open(PANCHANG_VAULT_FILE, "r", encoding="utf-8") as f:
                uploaded_panchang = json.load(f)
                if today_str in uploaded_panchang:
                    return uploaded_panchang[today_str]
        except Exception:
            pass

    if today_str in STATIC_PANCHANG:
        return STATIC_PANCHANG[today_str]
        
    stavan_tithi = fetch_tithi_from_stavan()
    if stavan_tithi:
        return stavan_tithi

    return "Tithi Pending Update"

def is_jain_or_ai_query(query: str) -> bool:
    lower = query.lower()
    keywords = [
        "jain", "jainism", "panchang", "tithi", "stavan", 
        "ai", "artificial intelligence", "gemini", "image", "generate", "draw", "edit"
    ]
    return any(word in lower for word in keywords)

def text_to_speech_audio(text: str, lang_code: str) -> bytes:
    clean_text = re.sub(r'<[^>]*>', '', text)  # Strip HTML tags for cleaner speech
    tts = gTTS(text=clean_text, lang=lang_code, slow=False)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp.read()

# ------------------------------------------------------------------------------
# 4. SESSION STATE & DAILY CREDIT QUOTA TRACKER (50 CREDITS)
# ------------------------------------------------------------------------------
MAX_CREDITS = 50
current_time = time.time()

if 'user_credits' not in st.session_state: 
    st.session_state.user_credits = MAX_CREDITS
if 'last_credit_reset' not in st.session_state: 
    st.session_state.last_credit_reset = current_time
if 'chat_history' not in st.session_state: 
    st.session_state.chat_history = []
if 'app_lang' not in st.session_state: 
    st.session_state.app_lang = "English"

if current_time - st.session_state.last_credit_reset >= 86400:
    st.session_state.user_credits = MAX_CREDITS
    st.session_state.last_credit_reset = current_time

ui_labels = {
    "English": {"hist": "Recent History", "pan": "Panchang Info", "ask": "Ask SamyakAI logic...", "upload": "Upload File / Image", "lang_code": "en"},
    "Hindi": {"hist": "इतिहास", "pan": "पंचांग जानकारी", "ask": "तर्क पूछें...", "upload": "फाइल / फोटो अपलोड करें", "lang_code": "hi"},
    "Gujarati": {"hist": "ઇતિહાસ", "pan": "પંચાંગ માહિતી", "ask": "તर्क પૂછો...", "upload": "ફાઇલ / ફોટો અપલોડ કરો", "lang_code": "gu"},
    "Marathi": {"hist": "इतिहास", "pan": "પંચાંગ माहिती", "ask": "तर्क विचारा...", "upload": "फाइल / फोटो टाका", "lang_code": "mr"}
}
labels = ui_labels.get(st.session_state.app_lang, ui_labels["English"])

# ------------------------------------------------------------------------------
# 5. SIDEBAR NAVIGATION & SETTINGS
# ------------------------------------------------------------------------------
with st.sidebar:
    # Try displaying logo image in sidebar if available
    if os.path.exists("logo.png"):
        st.image("logo.png", width=80)
    
    st.title("Samyak Navigation")
    
    st.subheader("⚙️ Settings & Audio")
    st.session_state.app_lang = st.selectbox(
        "🌐 Language", 
        ["English", "Hindi", "Gujarati", "Marathi"],
        index=["English", "Hindi", "Gujarati", "Marathi"].index(st.session_state.app_lang)
    )
    
    enable_voice_output = st.checkbox("🔊 Enable Voice Readout (TTS)", value=True)
    
    st.divider()
    
    live_date = datetime.date.today().strftime("%d-%m-%Y")
    st.subheader(f"📅 {labels['pan']}")
    st.metric(label="Date (English)", value=live_date)
    st.metric(label="Tithi", value=get_tithi())
    
    st.divider()
    
    st.markdown(f"""
        <div style="background: #1e1e2f; border: 1px solid #4a4a6a; border-radius: 12px; padding: 12px; margin-bottom: 15px;">
            <span style="font-weight: 700; color: #e0e0e0;">GEMINI CREDITS: </span>
            <span style="font-size: 18px; font-weight: bold; color: #00d2ff;">{st.session_state.user_credits} / {MAX_CREDITS}</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.subheader(f"📜 {labels['hist']}")
    if st.session_state.chat_history:
        for chat in reversed(st.session_state.chat_history[-5:]):
            st.text(f"• {chat.get('title', 'Query')[:25]}...")
    else:
        st.text("No history yet.")

# ------------------------------------------------------------------------------
# 6. APP HEADER
# ------------------------------------------------------------------------------
st.markdown("<h1 style='text-align: center;'>Your Jain AI-Question Companion</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: right; color: #888;'>- MADE BY STAVYA SHAH</p>", unsafe_allow_html=True)
st.divider()

for item in st.session_state.chat_history:
    with st.chat_message(item["role"]):
        st.markdown(item["content"], unsafe_allow_html=True)
        if item.get("uploaded_img"):
            st.image(item["uploaded_img"], caption="Vault Image", width=300)
        if item.get("generated_img"):
            st.image(item["generated_img"], caption="Generated Canvas Output", use_column_width=True)
            buf = io.BytesIO()
            item["generated_img"].save(buf, format="PNG")
            st.download_button(
                label="📥 Download High-Res Output",
                data=buf.getvalue(),
                file_name="canvas_artwork.png",
                mime="image/png",
                key=f"dl_{item['id']}"
            )
        if item.get("audio_bytes") and item["role"] == "assistant":
            st.audio(item["audio_bytes"], format="audio/mp3")

# ------------------------------------------------------------------------------
# 7. CANVAS BAR & GAMMA-STYLE POPOVER SETTINGS
# ------------------------------------------------------------------------------
st.markdown("---")

c1, c2, c3 = st.columns([2, 2, 3])

with c1:
    force_image_mode = st.toggle("🎨 Force Canvas Image Mode", value=False)

with c2:
    with st.popover("🖼️ Canvas Image Settings"):
        st.markdown("### Image Parameters (Gamma-style)")
        selected_ratio = st.selectbox("Aspect Ratio", ["1:1", "16:9", "9:16", "4:3", "3:4"], index=0)
        selected_style = st.selectbox("Artistic Style", ["Default", "Ghibli Anime", "Photorealistic", "Digital Painting", "3D Render", "Vibrant Sketch"])
        selected_lighting = st.selectbox("Lighting & Ambience", ["Natural", "Cinematic", "Studio Golden Hour", "Neon Cyberpunk"])
        selected_detail = st.select_slider("Detail Level", options=["Standard", "High-Definition", "Ultra-Detailed 8K"])

with c3:
    uploaded_file = st.file_uploader(labels["upload"], type=["png", "jpg", "jpeg", "json"], disabled=force_image_mode)

placeholder = "Enter prompt to generate Canvas Image..." if force_image_mode else labels["ask"]
user_prompt = st.chat_input(placeholder)

# ------------------------------------------------------------------------------
# 8. EXECUTION ENGINE
# ------------------------------------------------------------------------------
if user_prompt:
    cost = 5 if force_image_mode else 1
    
    if st.session_state.user_credits < cost:
        st.error("24-Hour Credit Limit Reached! Quota resets tomorrow.")
    else:
        st.session_state.user_credits -= cost
        msg_id = len(st.session_state.chat_history)
        
        # BRANCH A: CANVAS IMAGE GENERATION
        if force_image_mode:
            complex_prompt = user_prompt
            if selected_style != "Default":
                complex_prompt += f", in {selected_style} style"
            if selected_lighting != "Natural":
                complex_prompt += f", {selected_lighting} lighting"
            if selected_detail != "Standard":
                complex_prompt += f", {selected_detail}"

            st.session_state.chat_history.append({
                "id": msg_id,
                "role": "user",
                "title": user_prompt,
                "content": f"🎨 **Canvas Image Prompt:** {complex_prompt} | **Ratio:** {selected_ratio}"
            })
            
            with st.spinner(f"Rendering high-definition image ({selected_ratio})..."):
                try:
                    result = client.models.generate_images(
                        model="imagen-3.0-generate-002",
                        prompt=complex_prompt,
                        config=types.GenerateImagesConfig(
                            number_of_images=1,
                            aspect_ratio=selected_ratio,
                        )
                    )
                    
                    for gen_img in result.generated_images:
                        img_bytes = gen_img.image.image_bytes
                        pil_img = Image.open(io.BytesIO(img_bytes))
                        
                        st.session_state.chat_history.append({
                            "id": msg_id + 1,
                            "role": "assistant",
                            "title": user_prompt,
                            "content": f"Generated image for: *\"{complex_prompt}\"*",
                            "generated_img": pil_img
                        })
                        st.rerun()

                except Exception as e:
                    st.error(f"Imagen 3 Generation Error: {str(e)}")

        # BRANCH B: TEXT & VISION ANALYSIS
        else:
            uploaded_pil = Image.open(uploaded_file) if uploaded_file and uploaded_file.type.startswith("image/") else None
            
            if uploaded_file and uploaded_file.name.endswith(".json"):
                with open(PANCHANG_VAULT_FILE, "wb") as pf:
                    pf.write(uploaded_file.getbuffer())
                st.success("Integrated new Panchang JSON dataset into Vault!")

            st.session_state.chat_history.append({
                "id": msg_id,
                "role": "user",
                "title": user_prompt,
                "content": user_prompt,
                "uploaded_img": uploaded_pil
            })
            
            with st.spinner("Processing request..."):
                try:
                    system_instructions = f"""
                    DATE: {live_date}
                    CURRENT TITHI: {get_tithi()}
                    QUERY: {user_prompt}
                    STRICT RULES:
                    1. Answer in language: {st.session_state.app_lang}.
                    2. Maintain tithi information context where applicable.
                    3. Only Jainism or AI content is valid. If unrelated, answer in red text: "This software is designed for questions related to Jainism or AI."
                    """
                    
                    if uploaded_pil:
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=[uploaded_pil, system_instructions]
                        )
                    else:
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=system_instructions
                        )
                    
                    answer_text = response.text
                    formatted_answer = answer_text if is_jain_or_ai_query(user_prompt) else f"<div style='color:red'>{answer_text}</div>"
                    
                    audio_data = None
                    if enable_voice_output:
                        try:
                            audio_data = text_to_speech_audio(answer_text, labels["lang_code"])
                        except Exception:
                            pass
                    
                    st.session_state.chat_history.append({
                        "id": msg_id + 1,
                        "role": "assistant",
                        "title": user_prompt,
                        "content": formatted_answer,
                        "audio_bytes": audio_data
                    })
                    st.rerun()

                except Exception as e:
                    st.error(f"Processing Error: {str(e)}")
