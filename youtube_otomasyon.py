import streamlit as st
import anthropic
import requests
import json
import os
import tempfile
import time
from pathlib import Path

# ─────────────────────────────────────────────
# SAYFA AYARLARI
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="YouTube İçerik Otomasyonu",
    page_icon="🎬",
    layout="wide"
)

st.markdown("""
<style>
    .main { background-color: #0f0f0f; }
    .stApp { background-color: #0f0f0f; color: #ffffff; }
    .block-container { padding: 2rem; }
    .stButton>button {
        background: linear-gradient(135deg, #ff0000, #cc0000);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: bold;
        width: 100%;
    }
    .stButton>button:hover { background: linear-gradient(135deg, #cc0000, #990000); }
    .step-box {
        background: #1a1a1a;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .success-box {
        background: #0d2b0d;
        border: 1px solid #1a6b1a;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    h1, h2, h3 { color: #ffffff; }
    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea,
    .stSelectbox>div>div>select {
        background-color: #1a1a1a;
        color: #ffffff;
        border: 1px solid #444;
        border-radius: 8px;
    }
    .sidebar .sidebar-content { background-color: #111; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR — API KEY GİRİŞİ
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔑 API Ayarları")
    st.markdown("---")

    anthropic_key = st.text_input(
        "Anthropic API Key", type="password",
        placeholder="sk-ant-...",
        help="claude.ai → Settings → API Keys"
    )
    openai_key = st.text_input(
        "OpenAI API Key (Whisper)", type="password",
        placeholder="sk-...",
        help="platform.openai.com → API Keys"
    )
    pexels_key = st.text_input(
        "Pexels API Key", type="password",
        placeholder="...",
        help="pexels.com/api — Ücretsiz"
    )
    unsplash_key = st.text_input(
        "Unsplash Access Key", type="password",
        placeholder="...",
        help="unsplash.com/developers — Ücretsiz"
    )

    st.markdown("---")
    st.markdown("### 📁 YouTube OAuth")
    yt_cred_file = st.file_uploader(
        "client_secrets.json yükle",
        type=["json"],
        help="Google Cloud Console → OAuth 2.0 → Desktop App"
    )
    if yt_cred_file:
        st.success("✅ YouTube credentials yüklendi")

    st.markdown("---")
    st.markdown("### 📊 Maliyet Tahmini")
    st.info("💡 Whisper: ~$0.006/dk\nClaude: ~$0.01/istek\nPexels/Unsplash: Ücretsiz")

# ─────────────────────────────────────────────
# BAŞLIK
# ─────────────────────────────────────────────
st.markdown("# 🎬 YouTube İçerik Otomasyonu")
st.markdown("Ses → Metin → SEO İçerik → Görsel → Video → YouTube")
st.markdown("---")

# ─────────────────────────────────────────────
# 4 SEKME
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🎙️ 1. Ses → Metin",
    "✍️ 2. SEO İçerik",
    "🖼️ 3. Görsel & Video",
    "📤 4. YouTube Yükle"
])

# ══════════════════════════════════════════════
# TAB 1: SES → METİN (WHISPER)
# ══════════════════════════════════════════════
with tab1:
    st.markdown("### 🎙️ Ses Dosyasını Metne Çevir")
    st.markdown('<div class="step-box">', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        audio_file = st.file_uploader(
            "Ses dosyası yükle",
            type=["mp3", "mp4", "wav", "m4a", "ogg", "webm"],
            help="Max 25MB (OpenAI limiti)"
        )
    with col2:
        whisper_lang = st.selectbox(
            "Dil",
            ["tr", "en", "de", "fr", "es", "ar"],
            help="Otomatik algılama için boş bırak"
        )
        whisper_model = st.selectbox(
            "Model",
            ["whisper-1"],
        )

    if audio_file:
        file_size_mb = audio_file.size / (1024 * 1024)
        st.info(f"📁 Dosya: **{audio_file.name}** | Boyut: **{file_size_mb:.1f} MB**")
        est_duration = file_size_mb * 0.8  # kaba tahmin
        st.caption(f"💰 Tahmini maliyet: ~${est_duration * 0.006:.3f}")

    if st.button("🚀 Metne Çevir", key="btn_whisper"):
        if not openai_key:
            st.error("❌ OpenAI API key gerekli!")
        elif not audio_file:
            st.error("❌ Ses dosyası yükleyin!")
        else:
            with st.spinner("🎧 Whisper işliyor..."):
                try:
                    with tempfile.NamedTemporaryFile(
                        suffix=f".{audio_file.name.split('.')[-1]}",
                        delete=False
                    ) as tmp:
                        tmp.write(audio_file.read())
                        tmp_path = tmp.name

                    with open(tmp_path, "rb") as f:
                        response = requests.post(
                            "https://api.openai.com/v1/audio/transcriptions",
                            headers={"Authorization": f"Bearer {openai_key}"},
                            files={"file": (audio_file.name, f, audio_file.type)},
                            data={
                                "model": whisper_model,
                                "language": whisper_lang,
                                "response_format": "verbose_json"
                            }
                        )

                    os.unlink(tmp_path)

                    if response.status_code == 200:
                        result = response.json()
                        transcript = result.get("text", "")
                        duration = result.get("duration", 0)

                        st.session_state["transcript"] = transcript
                        st.session_state["audio_duration"] = duration

                        st.markdown('<div class="success-box">', unsafe_allow_html=True)
                        st.success(f"✅ Transkript hazır! ({duration:.0f} saniye, {len(transcript.split())} kelime)")
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.error(f"❌ Hata: {response.json()}")

                except Exception as e:
                    st.error(f"❌ {str(e)}")

    if "transcript" in st.session_state:
        st.markdown("#### 📝 Transkript")
        edited = st.text_area(
            "Düzenle (isteğe bağlı)",
            value=st.session_state["transcript"],
            height=300,
            key="transcript_edit"
        )
        st.session_state["transcript"] = edited
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "⬇️ TXT İndir",
                data=st.session_state["transcript"],
                file_name="transkript.txt",
                mime="text/plain"
            )
        with col2:
            if st.button("➡️ SEO İçerik Üretimine Geç"):
                st.info("Tab 2'ye geçin!")

    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 2: SEO İÇERİK (CLAUDE)
# ══════════════════════════════════════════════
with tab2:
    st.markdown("### ✍️ Claude ile SEO İçerik Üret")
    st.markdown('<div class="step-box">', unsafe_allow_html=True)

    if "transcript" not in st.session_state:
        st.warning("⚠️ Önce Tab 1'de transkript oluşturun, veya buraya manuel metin girin.")

    manual_text = st.text_area(
        "İçerik metni (transkript veya konu özeti)",
        value=st.session_state.get("transcript", ""),
        height=200,
        placeholder="Ses dosyanızın transkriptini veya video konusunu buraya yazın..."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        content_lang = st.selectbox("Dil", ["Türkçe", "İngilizce", "Almanca", "Arapça"])
    with col2:
        content_category = st.selectbox(
            "Kategori",
            ["Genel", "Teknoloji", "Eğitim", "İş/Finans", "Sağlık", "Yaşam Tarzı", "Eğlence"]
        )
    with col3:
        video_type = st.selectbox(
            "Video Tipi",
            ["Uzun form (10+ dk)", "Orta (3-10 dk)", "Shorts (< 60 sn)"]
        )

    target_audience = st.text_input(
        "Hedef kitle (isteğe bağlı)",
        placeholder="Örn: 25-45 yaş, girişimciler, Türkiye"
    )

    if st.button("🤖 Claude ile SEO İçerik Üret", key="btn_claude"):
        if not anthropic_key:
            st.error("❌ Anthropic API key gerekli!")
        elif not manual_text.strip():
            st.error("❌ İçerik metni boş!")
        else:
            with st.spinner("🧠 Claude düşünüyor..."):
                try:
                    client = anthropic.Anthropic(api_key=anthropic_key)

                    prompt = f"""Sen bir YouTube SEO uzmanısın. Aşağıdaki içerik/transkript için kapsamlı YouTube SEO paketi hazırla.

İÇERİK:
{manual_text[:3000]}

PARAMETRELER:
- Dil: {content_lang}
- Kategori: {content_category}
- Video tipi: {video_type}
- Hedef kitle: {target_audience or 'Genel'}

ÇIKTI FORMATI (tam olarak bu JSON yapısında döndür):
{{
  "basliklar": [
    "Başlık 1 (60 karakter altı, güçlü anahtar kelime)",
    "Başlık 2 (alternatif, merak uyandıran)",
    "Başlık 3 (sayı/liste formatı)"
  ],
  "aciklama": "500-1000 kelime YouTube açıklaması. İlk 2 satır önemli (arama önizlemesi). Anahtar kelimeler doğal yerleştirilmiş. CTA eklenmiş. Zaman damgaları için yer bırakılmış.",
  "etiketler": ["etiket1", "etiket2", "...en fazla 15 etiket"],
  "thumbnail_metin": "Thumbnail için kısa, dikkat çekici metin (max 4 kelime)",
  "thumbnail_prompt": "İngilizce görsel arama terimi Pexels/Unsplash için",
  "ana_anahtar_kelime": "En önemli tek anahtar kelime",
  "kisa_ozet": "Video için 2 cümle özet",
  "hashtag": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"]
}}

SADECE JSON döndür, başka hiçbir şey yazma."""

                    message = client.messages.create(
                        model="claude-opus-4-5",
                        max_tokens=2000,
                        messages=[{"role": "user", "content": prompt}]
                    )

                    raw = message.content[0].text.strip()
                    # JSON temizle
                    if raw.startswith("```"):
                        raw = raw.split("```")[1]
                        if raw.startswith("json"):
                            raw = raw[4:]
                    raw = raw.strip()

                    seo_data = json.loads(raw)
                    st.session_state["seo_data"] = seo_data

                    st.success("✅ SEO paketi hazır!")

                except json.JSONDecodeError:
                    # JSON parse edilemezse raw göster
                    st.session_state["seo_data"] = {"raw": raw}
                    st.warning("⚠️ JSON parse hatası, ham çıktı gösteriliyor.")
                except Exception as e:
                    st.error(f"❌ {str(e)}")

    # SEO Sonuçları Göster
    if "seo_data" in st.session_state:
        data = st.session_state["seo_data"]

        if "raw" in data:
            st.text_area("Ham Çıktı", value=data["raw"], height=400)
        else:
            st.markdown("---")
            st.markdown("#### 🎯 Başlıklar")
            for i, baslik in enumerate(data.get("basliklar", []), 1):
                col1, col2 = st.columns([4, 1])
                with col1:
                    edited_baslik = st.text_input(f"Başlık {i}", value=baslik, key=f"baslik_{i}")
                with col2:
                    st.metric("Karakter", len(edited_baslik))
                if i == 1:
                    st.session_state["secili_baslik"] = edited_baslik

            st.markdown("#### 📄 Açıklama")
            aciklama = st.text_area(
                "YouTube Açıklaması",
                value=data.get("aciklama", ""),
                height=250,
                key="aciklama_edit"
            )
            st.session_state["aciklama"] = aciklama

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 🏷️ Etiketler")
                etiketler = data.get("etiketler", [])
                st.write(", ".join(etiketler))
                st.session_state["etiketler"] = etiketler

            with col2:
                st.markdown("#### # Hashtagler")
                hashtagler = data.get("hashtag", [])
                st.write(" ".join(hashtagler))

            st.markdown("#### 🖼️ Thumbnail")
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Metin:** {data.get('thumbnail_metin', '')}")
            with col2:
                st.info(f"**Görsel araması:** {data.get('thumbnail_prompt', '')}")
                st.session_state["gorsel_arama"] = data.get("thumbnail_prompt", "")

            # JSON indirme
            st.download_button(
                "⬇️ SEO Paketi İndir (JSON)",
                data=json.dumps(data, ensure_ascii=False, indent=2),
                file_name="seo_paketi.json",
                mime="application/json"
            )

    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 3: GÖRSEL & VİDEO
# ══════════════════════════════════════════════
with tab3:
    st.markdown("### 🖼️ Görsel Çek & Video Oluştur")
    st.markdown('<div class="step-box">', unsafe_allow_html=True)

    # GÖRSEL ARAMA
    st.markdown("#### 📷 Görsel Arama")
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        search_query = st.text_input(
            "Arama terimi (İngilizce)",
            value=st.session_state.get("gorsel_arama", ""),
            placeholder="technology business meeting"
        )
    with col2:
        gorsel_kaynak = st.selectbox("Kaynak", ["Pexels", "Unsplash"])
    with col3:
        gorsel_sayi = st.selectbox("Adet", [4, 8, 12])

    if st.button("🔍 Görsel Ara", key="btn_gorsel"):
        if not search_query:
            st.error("❌ Arama terimi girin!")
        elif gorsel_kaynak == "Pexels" and not pexels_key:
            st.error("❌ Pexels API key gerekli! Sidebar'dan girin.")
        elif gorsel_kaynak == "Unsplash" and not unsplash_key:
            st.error("❌ Unsplash API key gerekli! Sidebar'dan girin.")
        else:
            with st.spinner(f"🔍 {gorsel_kaynak}'ta aranıyor..."):
                try:
                    gorseller = []

                    if gorsel_kaynak == "Pexels":
                        resp = requests.get(
                            "https://api.pexels.com/v1/search",
                            headers={"Authorization": pexels_key},
                            params={"query": search_query, "per_page": gorsel_sayi, "orientation": "landscape"}
                        )
                        if resp.status_code == 200:
                            photos = resp.json().get("photos", [])
                            gorseller = [
                                {
                                    "url": p["src"]["large"],
                                    "thumb": p["src"]["medium"],
                                    "photographer": p["photographer"],
                                    "alt": p.get("alt", search_query)
                                }
                                for p in photos
                            ]

                    elif gorsel_kaynak == "Unsplash":
                        resp = requests.get(
                            "https://api.unsplash.com/search/photos",
                            headers={"Authorization": f"Client-ID {unsplash_key}"},
                            params={"query": search_query, "per_page": gorsel_sayi, "orientation": "landscape"}
                        )
                        if resp.status_code == 200:
                            results = resp.json().get("results", [])
                            gorseller = [
                                {
                                    "url": r["urls"]["regular"],
                                    "thumb": r["urls"]["small"],
                                    "photographer": r["user"]["name"],
                                    "alt": r.get("alt_description", search_query)
                                }
                                for r in results
                            ]

                    if gorseller:
                        st.session_state["gorseller"] = gorseller
                        st.success(f"✅ {len(gorseller)} görsel bulundu!")
                    else:
                        st.warning("⚠️ Görsel bulunamadı, farklı anahtar kelime deneyin.")

                except Exception as e:
                    st.error(f"❌ {str(e)}")

    # Görsel Galerisi
    if "gorseller" in st.session_state:
        st.markdown("#### 🖼️ Bulunan Görseller (birini seç)")
        gorseller = st.session_state["gorseller"]
        cols = st.columns(4)
        for i, g in enumerate(gorseller):
            with cols[i % 4]:
                st.image(g["thumb"], caption=f"📷 {g['photographer']}", use_container_width=True)
                if st.button(f"✅ Seç #{i+1}", key=f"gorsel_sec_{i}"):
                    st.session_state["secili_gorsel"] = g
                    st.success(f"Görsel #{i+1} seçildi!")

    if "secili_gorsel" in st.session_state:
        sg = st.session_state["secili_gorsel"]
        st.success(f"✅ Seçili görsel: {sg['alt']} (📷 {sg['photographer']})")

    # VİDEO OLUŞTURMA
    st.markdown("---")
    st.markdown("#### 🎬 Video Oluştur (MoviePy)")
    st.info("""
    **MoviePy** lokal kurulum gerektirir. Aşağıdaki adımları izle:
    
    ```bash
    pip install moviepy pillow
    ```
    
    Video oluşturma için gerekli dosyalar:
    - Arka plan görseli (seçildi ✅)
    - Ses dosyası (isteğe bağlı)
    - Başlık metni (SEO'dan gelir)
    """)

    col1, col2 = st.columns(2)
    with col1:
        video_sure = st.slider("Video süresi (saniye)", 30, 600, 120)
        video_cozunurluk = st.selectbox("Çözünürlük", ["1920x1080 (Full HD)", "1280x720 (HD)", "1080x1920 (Shorts)"])
    with col2:
        font_size = st.slider("Başlık font boyutu", 40, 120, 70)
        overlay_opacity = st.slider("Karartma oranı", 0.3, 0.8, 0.5)

    # MoviePy script oluştur
    if st.button("📄 MoviePy Scripti Oluştur", key="btn_moviepy"):
        baslik = st.session_state.get("secili_baslik", "Video Başlığı")
        gorsel_url = st.session_state.get("secili_gorsel", {}).get("url", "")

        cozunurluk_map = {
            "1920x1080 (Full HD)": (1920, 1080),
            "1280x720 (HD)": (1280, 720),
            "1080x1920 (Shorts)": (1080, 1920)
        }
        w, h = cozunurluk_map[video_cozunurluk]

        script = f'''#!/usr/bin/env python3
"""
YouTube Video Oluşturucu - MoviePy
Otomatik oluşturuldu: youtube_otomasyon.py
"""

from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import requests
import numpy as np
import textwrap
import os

# ─── AYARLAR ───
BASLIK = """{baslik}"""
GORSEL_URL = "{gorsel_url}"
SURE = {video_sure}
GENISLIK, YUKSEKLIK = {w}, {h}
FONT_BOYUT = {font_size}
OVERLAY_OPACITY = {overlay_opacity}
CIKTI_DOSYA = "youtube_video.mp4"

def gorsel_indir(url, kayit_yolu):
    r = requests.get(url, stream=True)
    with open(kayit_yolu, "wb") as f:
        for chunk in r.iter_content(1024):
            f.write(chunk)
    return kayit_yolu

def baslık_frame_olustur(baslik, genislik, yukseklik):
    """PIL ile başlık katmanı oluştur"""
    img = Image.new("RGBA", (genislik, yukseklik), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Karartma katmanı
    overlay = Image.new("RGBA", (genislik, yukseklik), 
                        (0, 0, 0, int(255 * OVERLAY_OPACITY)))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    
    # Metin (sistem fontu)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", FONT_BOYUT)
    except:
        font = ImageFont.load_default()
    
    # Metni ortala ve wrap et
    max_chars = int(genislik / (FONT_BOYUT * 0.55))
    satirlar = textwrap.wrap(baslik, width=max_chars)
    
    toplam_yukseklik = len(satirlar) * (FONT_BOYUT + 10)
    y_baslangic = (yukseklik - toplam_yukseklik) // 2
    
    for i, satir in enumerate(satirlar):
        bbox = draw.textbbox((0, 0), satir, font=font)
        metin_genislik = bbox[2] - bbox[0]
        x = (genislik - metin_genislik) // 2
        y = y_baslangic + i * (FONT_BOYUT + 10)
        
        # Gölge
        draw.text((x+3, y+3), satir, font=font, fill=(0, 0, 0, 200))
        # Ana metin
        draw.text((x, y), satir, font=font, fill=(255, 255, 255, 255))
    
    return np.array(img.convert("RGB"))

def video_olustur():
    print(f"🎬 Video oluşturuluyor: {{BASLIK[:50]}}")
    
    # Görseli indir
    gorsel_yolu = "temp_bg.jpg"
    if GORSEL_URL:
        print("📥 Arka plan görseli indiriliyor...")
        gorsel_indir(GORSEL_URL, gorsel_yolu)
    
    # Arka plan klibi
    if os.path.exists(gorsel_yolu):
        bg_clip = ImageClip(gorsel_yolu).set_duration(SURE)
        bg_clip = bg_clip.resize((GENISLIK, YUKSEKLIK))
    else:
        # Düz siyah arka plan
        bg_array = np.zeros((YUKSEKLIK, GENISLIK, 3), dtype=np.uint8)
        bg_clip = ImageClip(bg_array).set_duration(SURE)
    
    # Başlık katmanı
    baslik_array = baslık_frame_olustur(BASLIK, GENISLIK, YUKSEKLIK)
    baslik_clip = (ImageClip(baslik_array)
                   .set_duration(SURE)
                   .set_opacity(1.0)
                   .fadein(1.0)
                   .fadeout(1.0))
    
    # Klipleri birleştir
    final = CompositeVideoClip([bg_clip, baslik_clip])
    final = final.fadein(0.5).fadeout(0.5)
    
    # Ses dosyası varsa ekle
    ses_dosyasi = "ses.mp3"
    if os.path.exists(ses_dosyasi):
        ses = AudioFileClip(ses_dosyasi)
        ses = ses.subclip(0, min(SURE, ses.duration))
        final = final.set_audio(ses)
        print("🎵 Ses eklendi!")
    
    # Video kaydet
    print(f"💾 Video kaydediliyor: {{CIKTI_DOSYA}}")
    final.write_videofile(
        CIKTI_DOSYA,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="temp_audio.m4a",
        remove_temp=True,
        logger="bar"
    )
    
    print(f"✅ Tamamlandı: {{CIKTI_DOSYA}}")
    if os.path.exists(gorsel_yolu):
        os.remove(gorsel_yolu)

if __name__ == "__main__":
    video_olustur()
'''
        st.code(script, language="python")
        st.download_button(
            "⬇️ video_olustur.py İndir",
            data=script,
            file_name="video_olustur.py",
            mime="text/plain"
        )
        st.success("✅ Script hazır! Lokal çalıştır: `python video_olustur.py`")

    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 4: YOUTUBE YÜKLE
# ══════════════════════════════════════════════
with tab4:
    st.markdown("### 📤 YouTube'a Yükle")
    st.markdown('<div class="step-box">', unsafe_allow_html=True)

    # Yüklenecek video
    video_file = st.file_uploader(
        "Video dosyası seç (.mp4)",
        type=["mp4", "mov", "avi", "mkv"]
    )

    st.markdown("#### 📋 Video Bilgileri")

    baslik_default = st.session_state.get("secili_baslik", "")
    aciklama_default = st.session_state.get("aciklama", "")
    etiketler_default = st.session_state.get("etiketler", [])

    yt_baslik = st.text_input(
        "Başlık *",
        value=baslik_default,
        max_chars=100,
        help="Max 100 karakter"
    )
    st.caption(f"{len(yt_baslik)}/100 karakter")

    yt_aciklama = st.text_area(
        "Açıklama",
        value=aciklama_default,
        height=200,
        max_chars=5000
    )

    col1, col2 = st.columns(2)
    with col1:
        yt_etiketler = st.text_input(
            "Etiketler (virgülle ayır)",
            value=", ".join(etiketler_default),
            placeholder="etiket1, etiket2, etiket3"
        )
        yt_kategori = st.selectbox(
            "Kategori",
            {
                "22": "Kişiler & Bloglar",
                "27": "Eğitim",
                "28": "Bilim & Teknoloji",
                "24": "Eğlence",
                "25": "Haberler & Politika",
                "26": "Nasıl Yapılır & Stil",
                "10": "Müzik",
                "17": "Spor",
                "19": "Seyahat & Etkinlikler",
                "20": "Oyun"
            }.keys(),
            format_func=lambda x: {
                "22": "Kişiler & Bloglar", "27": "Eğitim",
                "28": "Bilim & Teknoloji", "24": "Eğlence",
                "25": "Haberler & Politika", "26": "Nasıl Yapılır & Stil",
                "10": "Müzik", "17": "Spor",
                "19": "Seyahat & Etkinlikler", "20": "Oyun"
            }[x]
        )
    with col2:
        yt_gizlilik = st.selectbox(
            "Gizlilik",
            ["private", "unlisted", "public"],
            format_func=lambda x: {
                "private": "🔒 Gizli",
                "unlisted": "🔗 Listelenmemiş",
                "public": "🌍 Herkese Açık"
            }[x]
        )
        yt_zamanlama = st.checkbox("⏰ Zamanlı yayın")

    if yt_zamanlama:
        col1, col2 = st.columns(2)
        with col1:
            yt_tarih = st.date_input("Yayın tarihi")
        with col2:
            yt_saat = st.time_input("Yayın saati")

    st.markdown("---")

    # YouTube Upload Scripti
    st.markdown("#### 🔧 YouTube API Kurulum Rehberi")
    with st.expander("📖 Adım adım YouTube API kurulumu"):
        st.markdown("""
        **1. Google Cloud Console:**
        - [console.cloud.google.com](https://console.cloud.google.com) → Yeni proje
        - APIs & Services → Enable APIs → "YouTube Data API v3"
        
        **2. OAuth Credentials:**
        - Credentials → Create Credentials → OAuth 2.0 Client ID
        - Application type: **Desktop App**
        - JSON dosyasını indir → Sidebar'dan yükle
        
        **3. Gerekli kütüphaneler:**
        ```bash
        pip install google-auth google-auth-oauthlib google-api-python-client
        ```
        
        **4. İlk çalıştırmada:**
        - Tarayıcıda Google hesabı onayı istenir
        - Token kaydedilir, sonraki çalıştırmalarda otomatik
        """)

    if st.button("📄 YouTube Upload Scripti Oluştur", key="btn_yt_script"):
        upload_script = f'''#!/usr/bin/env python3
"""
YouTube Video Yükleme Scripti
google-api-python-client gerektirir:
pip install google-auth google-auth-oauthlib google-api-python-client
"""

import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS = "client_secrets.json"
TOKEN_FILE = "youtube_token.json"

# ─── VIDEO BİLGİLERİ ───
VIDEO_DOSYASI = "youtube_video.mp4"
BASLIK = """{yt_baslik or 'Video Başlığı'}"""
ACIKLAMA = """{(yt_aciklama or '')[:500]}..."""
ETIKETLER = {[e.strip() for e in yt_etiketler.split(",") if e.strip()] if yt_etiketler else []}
KATEGORI = "{yt_kategori}"
GIZLILIK = "{yt_gizlilik}"

def youtube_baglan():
    """OAuth ile YouTube bağlantısı"""
    creds = None
    
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    
    return build("youtube", "v3", credentials=creds)

def video_yukle(youtube, video_dosyasi, baslik, aciklama, etiketler, kategori, gizlilik):
    """YouTube'a video yükle"""
    
    body = {{
        "snippet": {{
            "title": baslik,
            "description": aciklama,
            "tags": etiketler,
            "categoryId": kategori
        }},
        "status": {{
            "privacyStatus": gizlilik,
            "selfDeclaredMadeForKids": False
        }}
    }}
    
    media = MediaFileUpload(
        video_dosyasi,
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024*1024*10  # 10MB chunks
    )
    
    print(f"📤 Yükleniyor: {{baslik}}")
    print(f"🔒 Gizlilik: {{gizlilik}}")
    
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            yuzde = int(status.progress() * 100)
            print(f"⬆️ {{yuzde}}% yüklendi...")
    
    video_id = response["id"]
    print(f"✅ Yükleme tamamlandı!")
    print(f"🔗 https://youtube.com/watch?v={{video_id}}")
    return video_id

if __name__ == "__main__":
    if not os.path.exists(VIDEO_DOSYASI):
        print(f"❌ Video dosyası bulunamadı: {{VIDEO_DOSYASI}}")
        exit(1)
    
    print("🔐 YouTube bağlantısı kuruluyor...")
    youtube = youtube_baglan()
    
    video_id = video_yukle(
        youtube, VIDEO_DOSYASI, BASLIK, ACIKLAMA,
        ETIKETLER, KATEGORI, GIZLILIK
    )
    
    print(f"\\n🎉 Başarıyla yüklendi: https://youtube.com/watch?v={{video_id}}")
'''
        st.code(upload_script, language="python")
        st.download_button(
            "⬇️ youtube_yukle.py İndir",
            data=upload_script,
            file_name="youtube_yukle.py",
            mime="text/plain"
        )

    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🎬 YouTube İçerik Otomasyonu")
with col2:
    st.caption("⚡ Whisper + Claude + Pexels")
with col3:
    st.caption("🛠️ Streamlit ile çalışır")
