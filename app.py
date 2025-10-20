import streamlit as st
import tempfile
import whisper
import google.generativeai as genai
import os
from dotenv import load_dotenv

#Stremalit sayfa ayarları
st.set_page_config(
    page_title="AudioMind",
    page_icon="🎧",
)

#Uygulama başlığı ve açıklaması (HTML ile özel tasarım)
st.markdown("""
    <div style='background-color:black;padding:15px; border-radius:15px'>
        <h1 style='text-align:center;'>🎧 AudioMind</h1>
        <p style='text-align:center;'>Ses dosyanızı yükleyin, ardından metne çevirip özet oluşturabilirsiniz.</p>
    </div>
""", unsafe_allow_html=True)

#env dosyasından API anahtarlarını yükler
load_dotenv()

#Gemini API'yi yapılandır
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
#Gemini modeli seçimi
gemini_model = genai.GenerativeModel("models/gemini-2.5-flash-preview-09-2025")

#Özet oluşturma fonksiyonu
def generate_summary(text, style):
    prompt = f"Aşağıdaki metni {style} biçiminde özetle:\n\n{text}"
    response = gemini_model.generate_content(prompt)
    return getattr(response, "text",str(response))



#CSS ile buton tasarımı
st.markdown("""
    <style>
        .stButton > button {
            background-color:#FF2400 !important;
            color: black;
            border: none;
            padding: 8px 20px;
            border-radius: 8px;
            font-weight: 700 !important;
            width: 100%;
            transition: background-color 0.2s ease;
        }
    
        .stButton > button:hover {
            background-color: #FF5500 !important;
            color: black;
        }
    </style>
""", unsafe_allow_html = True)

#Whisper modeli yükleme
if "model" not in st.session_state:
    with st.spinner("🎧 AI modelleri yükleniyor, lütfen bekleyiniz..."):
        st.session_state.model = whisper.load_model("base")
    st.balloons()
    st.success("Model yüklendi!")
# Modeli session state üzerinden al
model = st.session_state.model

#Üç sekmeli arayüz
tab1, tab2, tab3 = st.tabs(["1️⃣ Ses Yükle", "2️⃣ Metne Çevir", "3️⃣ Özetle"])

#1. Sekme ses dosyası yükleme alanı
with tab1:
    st.info("🎵 Bu sekmeye bir ses dosyası yükleyebilirsiniz.")
    audio_file = st.file_uploader("Bir ses dosyası yükleyiniz!", type=["mp3","wav","m4a"])

    if audio_file:
        #Yeni dosya yüklenirse eski session_state temizlenir
        if "audio_bytes" not in st.session_state or st.session_state.get("last_uploaded_name") != audio_file.name:
            st.session_state["audio_bytes"] = audio_file.read()
            st.session_state["last_uploaded_name"] = audio_file.name
            
            #Önceki transkript varsa temizler
            st.session_state.pop("transcript", None)
            st.session_state.pop("summary", None)
        
        #Ses dosyasını oynatır
        st.audio(st.session_state["audio_bytes"]) # Ses oynat
        st.info(f"🎵 Yüklenen dosya: **{audio_file.name}**")
        st.success("Dosya yüklendi ve çalınabiliyor!")
    else :
        st.error("Lütfen bir ses dosyası yükleyiniz!")

#2. Sekme: Sesi metne çevirir
with tab2:
    st.info("📝 Bu sekmede yüklediğiniz ses dosyasını yazıya dönüştürebilirsiniz.")
    if "audio_bytes" in st.session_state:
        if st.button("Metne Çevir"):
            with st.spinner("Ses metne çeviriliyor"):
                #Geçici dosya olustur
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                    tmp.write(st.session_state["audio_bytes"])
                    tmp_path = tmp.name
                try:
                #Whisper modeli transkripsiyon işlemi
                    result = model.transcribe(tmp_path)
                    transcript = result.get("text","")
                    st.session_state["transcript"] =transcript
                except Exception as e:
                    st.error(f"Transkripsiyon hatası {e}:")
                finally:
                    #Geçici dosyayı sil
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
        #Transkript i gizler ya da gösterir
        if "transcript" in st.session_state:
            with st.expander("📝 Transcript'i Göster / Gizle"):
                st.write(st.session_state["transcript"])

#3. Sekme: Metni özetleme
with tab3:
    st.info("💡 Bu sekmede metni kısa, detaylı ve ya madde madde biçiminde özetleyebilirsiniz.")
    if "transcript" in st.session_state:

        summary_style = st.radio(
            "Özet tarzını seçin:",
            ["Kısa","Detaylı","Madde madde"],
            index=0
        )
        if st.button("Gemini ile özetle"):
            if not gemini_model:
                st.error("Gemini yapılandırılması bulunamadı")
            else:
                with st.spinner("Gemini özet oluşturuyor"):
                    try:
                        summary = generate_summary(st.session_state["transcript"],summary_style)
                        st.session_state["summary"] = summary
                    except Exception as e:
                        st.error(f"özetleme hatası: {e}")
    #Özet oluşturulduysa gösterir
    if "summary" in st.session_state:
        st.success("✅ Özet başarıyla oluşturuldu!")
        st.subheader("Özet: ")
        st.write(st.session_state["summary"])

        #Metin uzun olursa önceden uyarı verir
        text_length = len(st.session_state["transcript"])
        if text_length > 8000:
            st.warning("⚠️ Metin uzun görünüyor. Özetleme işlemi biraz uzun sürebilir.")
        
        #Özet indirme butonu
        summary_txt = st.session_state["summary"].encode("utf-8")
        st.download_button(
        label="📥 Özeti TXT olarak indir",
        data=summary_txt,
        file_name="ozet.txt",
        mime="text/plain"
        )
    #Tüm verileri sıfırla butonu
    if st.button("🗑️ Tümünü Sıfırla"):
        for key in ["audio_bytes","transcript","summary","last_uploaded_name"]:
            st.session_state.pop(key, None)
        st.rerun()

#Footer
st.markdown("<hr>", unsafe_allow_html=True)
st.caption("AudioMind - Whisper + Gemini destekli ses özetleme aracı")
