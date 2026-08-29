# ==============================================================================
# PROJECT: SamyakAI Studio - Comprehensive Jain AI Question & Multimedia Companion
# AUTHOR: Stavya Shah
# DESCRIPTION: Full-featured Streamlit application supporting multi-language
# localization (English, Hindi, Gujarati, Marathi), dynamic Panchang lookups,
# advanced text-to-speech voice profiles, credit tracking, and free canvas
# image generation via Pollinations.ai.
# ==============================================================================

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


# ==============================================================================
# SECTION 1: PAGE CONFIGURATION & INITIAL SESSION STATE MANAGEMENT
# ==============================================================================

st.set_page_config(
    page_title="SamyakAI Studio",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Global Constants Configuration
PANCHANG_VAULT_FILE = "panchang_vault.json"
MAX_CREDITS = 500
CREDIT_RESET_INTERVAL_SECONDS = 86400  # 24 Hours in seconds
CURRENT_TIMESTAMP = time.time()


# Initialize Session State Variables with Default Safety Fallbacks
if 'user_credits' not in st.session_state: 
    st.session_state.user_credits = MAX_CREDITS

if 'last_credit_reset' not in st.session_state: 
    st.session_state.last_credit_reset = CURRENT_TIMESTAMP

if 'chat_history' not in st.session_state: 
    st.session_state.chat_history = []

if 'app_lang' not in st.session_state: 
    st.session_state.app_lang = "English"

if 'pending_action' not in st.session_state: 
    st.session_state.pending_action = None

if 'processed_audio_id' not in st.session_state:
    st.session_state.processed_audio_id = None


# Automated Daily Credit Reset Logic
if CURRENT_TIMESTAMP - st.session_state.last_credit_reset >= CREDIT_RESET_INTERVAL_SECONDS:
    st.session_state.user_credits = MAX_CREDITS
    st.session_state.last_credit_reset = CURRENT_TIMESTAMP


# ==============================================================================
# SECTION 2: GOOGLE GENAI CLIENT INITIALIZATION & AUTHENTICATION
# ==============================================================================

def initialize_gemini_client():
    """Retrieves API keys safely from environment variables or Streamlit secrets."""
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        try:
            api_key = st.secrets.get("API_KEY")
        except Exception:
            api_key = None
            
    if not api_key:
        st.error(
            "🔑 CRITICAL ERROR: GEMINI_API_KEY not found! "
            "Please set it in your environment variables or Streamlit secrets configuration."
        )
        st.stop()
        
    return genai.Client(api_key=api_key)


client = initialize_gemini_client()


# ==============================================================================
# SECTION 3: PANCHANG, DATASET & SYSTEM HELPER FUNCTIONS
# ==============================================================================

STATIC_PANCHANG_REGISTRY = {
    "2026-08-28": "Shravan Sud 15",
    "2026-08-29": "Shravan Vad 1",
    "2026-08-30": "Shravan Vad 2",
    "2026-08-31": "Shravan Vad 3"
}


def fetch_tithi_from_stavan() -> str:
    """Attempts to scrape live tithi data from external reference sources safely."""
    target_url = "https://stavan.com/"
    headers_config = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        request_obj = urllib.request.Request(target_url, headers=headers_config)
        with urllib.request.urlopen(request_obj, timeout=4) as response:
            html_content = response.read().decode('utf-8', errors='ignore')
            regex_pattern = r"([A-Za-z]+)\s+(Sud|Vad|Shukla|Krishna)\s+(\d{1,2})"
            match_result = re.search(regex_pattern, html_content, re.IGNORECASE)
            
            if match_result:
                month_name = match_result.group(1).capitalize()
                lunar_phase = 'Sud' if match_result.group(2).capitalize() in ['Sud', 'Shukla'] else 'Vad'
                lunar_day = match_result.group(3)
                return f"{month_name} {lunar_phase} {lunar_day}"
                
    except Exception as network_error:
        pass
        
    return ""


def get_tithi() -> str:
    """Resolves current tithi using uploaded vault files, static registries, or scrapers."""
    today_date_str = datetime.date.today().strftime("%Y-%m-%d")
    
    # Priority 1: User Uploaded Panchang JSON Vault File
    if os.path.exists(PANCHANG_VAULT_FILE):
        try:
            with open(PANCHANG_VAULT_FILE, "r", encoding="utf-8") as vault_file:
                vault_data = json.load(vault_file)
                if today_date_str in vault_data:
                    return vault_data[today_date_str]
        except Exception as vault_load_error:
            pass

    # Priority 2: Static Built-in Panchang Registry Lookup
    if today_date_str in STATIC_PANCHANG_REGISTRY:
        return STATIC_PANCHANG_REGISTRY[today_date_str]
        
    # Priority 3: Dynamic Web Lookup
    scraped_tithi = fetch_tithi_from_stavan()
    if scraped_tithi:
        return scraped_tithi

    return "Tithi Pending Update"


def validate_query_content(query_text: str) -> bool:
    """Validates user input text for basic structural integrity."""
    if not query_text or not isinstance(query_text, str):
        return False
        
    if len(query_text.strip()) == 0:
        return False
        
    return True


# ==============================================================================
# SECTION 4: AUDIO SYNTHESIS & MULTI-ACCENT GENDER ENGINE
# ==============================================================================

def text_to_speech_audio(text_to_read: str, language_code: str, voice_profile_selection: str) -> bytes:
    sanitized_text = re.sub(r'<[^>]*>', '', text_to_read)
    sanitized_text = re.sub(r'[*_#`]', '', sanitized_text)
    
    profile_mapping_rules = {
        "Male 1 (Indian Accent)": {"tld": "co.in", "slow_setting": False, "pitch_mod": "male_hi"},
        "Female 1 (Indian Accent)": {"tld": "co.in", "slow_setting": True, "pitch_mod": "fem_hi"},
        "Male 2 (US Accent)": {"tld": "com", "slow_setting": False, "pitch_mod": "male_us"},
        "Female 2 (US Accent)": {"tld": "ca", "slow_setting": False, "pitch_mod": "fem_us"}
    }
    
    configuration = profile_mapping_rules.get(voice_profile_selection, {"tld": "co.in", "slow_setting": False})
    normalized_language = language_code if language_code in ['en', 'hi', 'gu', 'mr'] else 'en'

    try:
        tts_engine = gTTS(text=sanitized_text, lang=normalized_language, tld=configuration["tld"], slow=configuration["slow_setting"])
        audio_buffer = io.BytesIO()
        tts_engine.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer.read()
    except Exception:
        return b""
        

# ==============================================================================
# SECTION 5: FREE POLLINATIONS.AI IMAGE GENERATION ENGINE
# ==============================================================================

def get_free_pollinations_image(prompt_text: str, aspect_ratio_setting: str = "1:1") -> str:
    """Constructs a fully formatted URL for zero-cost image generation via Pollinations.ai."""
    target_width, target_height = 1024, 1024
    
    if aspect_ratio_setting == "16:9":
        target_width, target_height = 1280, 720
    elif aspect_ratio_setting == "9:16":
        target_width, target_height = 720, 1280
    elif aspect_ratio_setting == "4:3":
        target_width, target_height = 1024, 768
    elif aspect_ratio_setting == "3:4":
        target_width, target_height = 768, 1024
        
    encoded_url_prompt = urllib.parse.quote(prompt_text)
    image_endpoint = f"https://image.pollinations.ai/prompt/{encoded_url_prompt}?width={target_width}&height={target_height}&nologo=true"
    
    return image_endpoint


# ==============================================================================
# SECTION 6: LOCALIZED UI LABELS & MULTI-LANGUAGE DICTIONARIES
# ==============================================================================

ui_translation_registry = {
    "English": {
        "title": "Your Jain AI-Question Companion",
        "nav_title": "Samyak Navigation",
        "settings": "⚙️ Settings & Voice",
        "lang_label": "🌐 Language",
        "voice_toggle": "🔊 Enable Voice Readout",
        "voice_profile": "🎙️ Select Voice Profile",
        "hist": "Recent History", 
        "pan": "Panchang Info", 
        "ask": "Ask SamyakAI logic...", 
        "upload": "Upload File / Image", 
        "lang_code": "en"
    },
    "Hindi": {
        "title": "आपका जैन एआई-प्रश्न साथी",
        "nav_title": "सम्यक नेविगेशन",
        "settings": "⚙️ सेटिंग्स और आवाज़",
        "lang_label": "🌐 भाषा",
        "voice_toggle": "🔊 आवाज़ से पढ़ना सक्षम करें",
        "voice_profile": "🎙️ आवाज़ प्रोफाइल चुनें",
        "hist": "इतिहास", 
        "pan": "पंचांग जानकारी", 
        "ask": "तर्क पूछें...", 
        "upload": "फाइल / फोटो अपलोड करें", 
        "lang_code": "hi"
    },
    "Gujarati": {
        "title": "તમારો જૈન એઆઈ-પ્રશ્ન સાથી",
        "nav_title": "સમ્યક નેવિગેશન",
        "settings": "⚙️ સેટિંગ્સ અને અવાજ",
        "lang_label": "🌐 ભાષા",
        "voice_toggle": "🔊 અવાજ દ્વારા વાંચન સક્ષમ કરો",
        "voice_profile": "🎙️ અવાજ પ્રોફાઇલ પસંદ કરો",
        "hist": "ઇતિહાસ", 
        "pan": "પંચાંગ માહિતી", 
        "ask": "તર્ક પૂછો...", 
        "upload": "ફાઇલ / ફોટો અપલોડ કરો", 
        "lang_code": "gu"
    },
    "Marathi": {
        "title": "तुमचा जैन एआय-प्रश्न सोबती",
        "nav_title": "सम्यक नॅव्हिगेशन",
        "settings": "⚙️ सेटिंग्ज आणि आवाज",
        "lang_label": "🌐 भाषा",
        "voice_toggle": "🔊 आवाजात वाचणे सुरू करा",
        "voice_profile": "🎙️ आवाजाचा प्रकार निवडा",
        "hist": "इतिहास", 
        "pan": "पंचांग माहिती", 
        "ask": "तर्क विचारा...", 
        "upload": "फाइल / फोटो टाका", 
        "lang_code": "mr"
    }
}


def handle_language_update():
    """Callback function triggered when the sidebar language selector changes."""
    st.session_state.app_lang = st.session_state.lang_selector


active_ui_labels = ui_translation_registry.get(
    st.session_state.app_lang, 
    ui_translation_registry["English"]
)


# ==============================================================================
# SECTION 7: SIDEBAR NAVIGATION, METRICS & SETTINGS PANEL
# ==============================================================================

with st.sidebar:
    st.markdown(f"""
        <div style="background: #1e1e2f; border: 1.5px solid #00d2ff; border-radius: 8px; padding: 8px; text-align: center; margin-bottom: 18px; box-shadow: 0 3px 6px rgba(0,0,0,0.25);">
            <span style="font-size: 11px; font-weight: 700; color: #00d2ff; letter-spacing: 0.8px;">SAMYAKAI CREDITS</span><br>
            <span style="font-size: 18px; font-weight: bold; color: #ffffff;">{st.session_state.user_credits} / {MAX_CREDITS}</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.title(active_ui_labels["nav_title"])
    st.subheader(active_ui_labels["settings"])
    
    st.selectbox(
        active_ui_labels["lang_label"], 
        ["English", "Hindi", "Gujarati", "Marathi"],
        index=["English", "Hindi", "Gujarati", "Marathi"].index(st.session_state.app_lang),
        key="lang_selector",
        on_change=handle_language_update
    )
    
    enable_voice_output = st.checkbox(active_ui_labels["voice_toggle"], value=True)
    
    selected_voice_profile = st.selectbox(
        active_ui_labels["voice_profile"],
        [
            "Male 1 (Indian Accent)", 
            "Female 1 (Indian Accent)", 
            "Male 2 (US Accent)", 
            "Female 2 (US Accent)"
        ]
    )
    
    st.divider()
    
    formatted_current_date = datetime.date.today().strftime("%d-%m-%Y")
    st.subheader(f"📅 {active_ui_labels['pan']}")
    st.metric(label="System Date", value=formatted_current_date)
    st.metric(label="Calculated Tithi", value=get_tithi())
    
    st.divider()
    
    st.subheader(f"📜 {active_ui_labels['hist']}")
    
    if st.session_state.chat_history:
        for chat_item in reversed(st.session_state.chat_history[-5:]):
            truncated_title = chat_item.get('title', 'Query')[:28]
            st.text(f"• {truncated_title}...")
    else:
        st.text("No query history recorded yet.")


# ==============================================================================
# SECTION 8: APPLICATION HEADER & CHAT HISTORY RENDERER
# ==============================================================================

if os.path.exists("logo.png"):
    st.image("logo.png", width=380)

st.markdown(f"<h1>{active_ui_labels['title']}</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #888; margin-top: -15px;'>- CREATED AND MAINTAINED BY STAVYA SHAH</p>", unsafe_allow_html=True)
st.divider()


for chat_message in st.session_state.chat_history:
    with st.chat_message(chat_message["role"]):
        st.markdown(chat_message["content"], unsafe_allow_html=True)
        
        if chat_message.get("uploaded_img"):
            st.image(chat_message["uploaded_img"], caption="Vault Image Reference", width=300)
            
        if chat_message.get("generated_url"):
            st.image(chat_message["generated_url"], caption="Generated Free Canvas Output", use_column_width=True)
            st.markdown(f"[📥 Download Image Directly]({chat_message['generated_url']})", unsafe_allow_html=True)
            
        if chat_message.get("audio_bytes") and chat_message["role"] == "assistant":
            st.audio(chat_message["audio_bytes"], format="audio/mp3")


# ==============================================================================
# SECTION 9: CANVAS CONTROLS, POPOVER SETTINGS & MULTIMEDIA INPUT WIDGETS
# ==============================================================================

st.markdown("---")
column_input_1, column_input_2, column_input_3 = st.columns([2, 2, 3])

with column_input_1:
    force_image_mode = st.toggle("🎨 Force Canvas Image Mode", value=False)

with column_input_2:
    with st.popover("🖼️ Canvas & Audio Studio Settings"):
        st.markdown("### Canvas Visual Parameters")
        selected_aspect_ratio = st.selectbox("Aspect Ratio", ["1:1", "16:9", "9:16", "4:3", "3:4"], index=0)
        selected_quality = st.selectbox("Render Quality", ["Standard", "High Definition (HD)", "Ultra 8K Cinematic"], index=0)
        selected_art_style = st.selectbox("Artistic Style", ["Default", "Ghibli Anime", "Photorealistic", "Digital Painting", "3D Render", "Vibrant Sketch"])
        selected_ambience = st.selectbox("Lighting & Ambience", ["Natural", "Cinematic", "Studio Golden Hour", "Neon Cyberpunk"])
        
        st.markdown("---")
        st.markdown("### 🎵 Music & Voice Cloning Engine")
        enable_music_generation = st.checkbox("🎶 Generate Sung Music/Lyrics Output", value=False)
        enable_voice_cloning = st.checkbox("🧬 Enable Custom Voice Cloning", value=False)
        cloned_voice_sample = st.file_uploader("Upload 5-10s MP3/WAV for Cloning", type=["mp3", "wav"], disabled=not enable_voice_cloning)

with column_input_3:
    uploaded_user_file = st.file_uploader(active_ui_labels["upload"], type=["png", "jpg", "jpeg", "json"], disabled=force_image_mode)

audio_input_recording = st.audio_input("🎤 Record Audio Query")
input_box_placeholder = "Enter prompt for canvas or lyrics..." if (force_image_mode or enable_music_generation) else active_ui_labels["ask"]
user_typed_prompt = st.chat_input(input_box_placeholder)
        

# ==============================================================================
# SECTION 10: MULTI-TIER ACTION EXECUTION & AUTOMATED INTENT ENGINE
# ==============================================================================

active_processed_prompt = user_typed_prompt

if audio_input_recording is not None and not user_typed_prompt:
    raw_audio_bytes = audio_input_recording.getvalue()
    computed_audio_hash = hash(raw_audio_bytes)
    if st.session_state.processed_audio_id != computed_audio_hash:
        st.session_state.processed_audio_id = computed_audio_hash
        active_processed_prompt = raw_audio_bytes
    else:
        active_processed_prompt = None

if active_processed_prompt and isinstance(active_processed_prompt, str):
    lower_prompt_check = active_processed_prompt.lower()
    if any(keyword in lower_prompt_check for keyword in ["generate an image", "create an image", "draw ", "paint ", "generate image"]):
        force_image_mode = True

if active_processed_prompt or uploaded_user_file:
    if force_image_mode or enable_music_generation:
        required_action_cost = 5
        action_descriptor_name = "🎨 Canvas Image / Sung Music Generation"
    elif uploaded_user_file is not None and not active_processed_prompt:
        required_action_cost = 0
        action_descriptor_name = "👁️ Image Reference & Analysis"
    elif uploaded_user_file is not None and active_processed_prompt:
        required_action_cost = 1
        action_descriptor_name = "✏️ Image Editing / Variation"
    else:
        required_action_cost = 1
        action_descriptor_name = "📜 Standard Query / Text Generation"

    if st.session_state.user_credits < required_action_cost:
        st.error(f"❌ Insufficient credits! '{action_descriptor_name}' requires {required_action_cost} credits, but you have {st.session_state.user_credits}.")
        st.stop()
    else:
        st.session_state.user_credits -= required_action_cost
        message_identifier = len(st.session_state.chat_history)
        display_prompt_string = "Audio Voice Query" if isinstance(active_processed_prompt, bytes) else (active_processed_prompt or "Image Reference Request")

        if force_image_mode:
            base_prompt_string = display_prompt_string if not isinstance(active_processed_prompt, bytes) else "Canvas generation from voice instruction"
            enhanced_canvas_prompt = base_prompt_string
            if selected_art_style != "Default":
                enhanced_canvas_prompt += f", in {selected_art_style} style"
            if selected_ambience != "Natural":
                enhanced_canvas_prompt += f", {selected_ambience} lighting"
            if selected_quality != "Standard":
                enhanced_canvas_prompt += f", {selected_quality} quality"

            st.session_state.chat_history.append({
                "id": message_identifier,
                "role": "user",
                "title": base_prompt_string,
                "content": f"🎨 **Canvas Prompt:** {enhanced_canvas_prompt} | **Aspect Ratio:** {selected_aspect_ratio} | **Quality:** {selected_quality}"
            })
            
            with st.spinner("Generating artwork layout..."):
                generated_image_url = get_free_pollinations_image(enhanced_canvas_prompt, selected_aspect_ratio)
                st.session_state.chat_history.append({
                    "id": message_identifier + 1,
                    "role": "assistant",
                    "title": base_prompt_string,
                    "content": f"Generated canvas artwork for: *\"{enhanced_canvas_prompt}\"*",
                    "generated_url": generated_image_url
                })
                st.rerun()

        elif enable_music_generation:
            base_lyrics_prompt = display_prompt_string if not isinstance(active_processed_prompt, bytes) else "Sung lyrics from audio instruction"
            st.session_state.chat_history.append({
                "id": message_identifier,
                "role": "user",
                "title": f"Sung Music: {base_lyrics_prompt}",
                "content": f"🎶 **Sung Lyrics Request:** {base_lyrics_prompt}"
            })
            
            with st.spinner("Synthesizing sung music and vocal track..."):
                music_generation_text = f"Sing these lyrics musically with rhythm and melody: {base_lyrics_prompt}"
                try:
                    api_response = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=[music_generation_text]
                    )
                    sung_response_text = api_response.text
                    synthesized_music_audio = text_to_speech_audio(sung_response_text, active_ui_labels["lang_code"], selected_voice_profile)
                except Exception:
                    sung_response_text = "Here is your musical arrangement for: " + base_lyrics_prompt
                    synthesized_music_audio = text_to_speech_audio(sung_response_text, active_ui_labels["lang_code"], selected_voice_profile)

                st.session_state.chat_history.append({
                    "id": message_identifier + 1,
                    "role": "assistant",
                    "title": f"Sung Music: {base_lyrics_prompt}",
                    "content": f"**Musical Output / Lyrics Arrangement:**\n\n{sung_response_text}",
                    "audio_bytes": synthesized_music_audio
                })
                st.rerun()

        else:
            loaded_pil_image = Image.open(uploaded_user_file) if uploaded_user_file and uploaded_user_file.type.startswith("image/") else None
            
            if uploaded_user_file and uploaded_user_file.name.endswith(".json"):
                with open(PANCHANG_VAULT_FILE, "wb") as vault_write_stream:
                    vault_write_stream.write(uploaded_user_file.getbuffer())
                st.success("Successfully integrated new Panchang JSON dataset into application vault!")

            st.session_state.chat_history.append({
                "id": message_identifier,
                "role": "user",
                "title": display_prompt_string,
                "content": display_prompt_string,
                "uploaded_img": loaded_pil_image
            })
            
            with st.spinner("Processing request using SamyakAI intelligence logic..."):
                try:
                    system_instructions_payload = (
                        f"SYSTEM DATE: {formatted_current_date}\n"
                        f"CURRENT ACTIVE TITHI: {get_tithi()}\n"
                        f"UI DEFAULT LANGUAGE SETTING: {st.session_state.app_lang}\n"
                        "STRICT RULES:\n"
                        "1. Detect the language and script of the user query or audio recording automatically.\n"
                        "2. Reply in that exact same language and script.\n"
                        "3. Keep formatting clean using standard markdown without any LaTeX formatting."
                    )
                    
                    gemini_contents_payload = []
                    if isinstance(active_processed_prompt, bytes):
                        gemini_contents_payload.append(types.Part.from_bytes(data=active_processed_prompt, mime_type="audio/wav"))
                        gemini_contents_payload.append("Please transcribe this audio recording accurately and respond directly in the speaker's language.")
                    else:
                        gemini_contents_payload.append(active_processed_prompt or "Please analyze this uploaded image and provide detailed visual feedback or image editing insights.")

                    gemini_contents_payload.append(system_instructions_payload)
                    if loaded_pil_image:
                        gemini_contents_payload.insert(0, loaded_pil_image)

                    api_response = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=gemini_contents_payload
                    )
                    
                    model_answer_text = api_response.text
                    target_tts_language_code = active_ui_labels["lang_code"]
                    if any(guar_char in model_answer_text for guar_char in ['અ', 'આ', 'ઇ', 'ઈ', 'ઉ', 'ઊ', 'એ', 'ઐ', 'ઓ', 'ઔ']):
                        target_tts_language_code = "gu"
                    elif any(hindi_char in model_answer_text for hindi_char in ['अ', 'आ', 'इ', 'ई', 'उ', 'ऊ', 'ए', 'ऐ', 'ओ', 'औ']):
                        target_tts_language_code = "hi"
                    elif any(marathi_char in model_answer_text for marathi_char in ['ळ']):
                        target_tts_language_code = "mr"

                    synthesized_audio_data = None
                    if enable_voice_output:
                        try:
                            synthesized_audio_data = text_to_speech_audio(model_answer_text, target_tts_language_code, selected_voice_profile)
                        except Exception:
                            pass
                    
                    st.session_state.chat_history.append({
                        "id": message_identifier + 1,
                        "role": "assistant",
                        "title": display_prompt_string,
                        "content": model_answer_text,
                        "audio_bytes": synthesized_audio_data
                    })
                    st.rerun()

                except Exception as execution_exception:
                    st.error(f"AI Execution Error Encountered
