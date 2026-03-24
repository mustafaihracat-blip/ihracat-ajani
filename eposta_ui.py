import streamlit as st
import pandas as pd
import smtplib
import time
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ========== SAYFA AYARI ==========
st.set_page_config(page_title="📧 E-Posta Gönderici", page_icon="📧", layout="centered")

st.title("📧 Otomatik E-Posta Gönderici")
st.markdown("---")

# ========== AYARLAR ==========
with st.sidebar:
    st.header("⚙️ SMTP Ayarları")
    smtp_server = st.text_input("SMTP Sunucu", value="mail.kursdegilkariyer.online")
    smtp_port = st.number_input("Port", value=587, step=1)
    email_user = st.text_input("E-posta", value="bilgi@kursdegilkariyer.online")
    email_pass = st.text_input("Şifre", value="Mustafa1234", type="password")
    aralik = st.number_input("E-postalar arası bekleme (saniye)", value=240, step=10,
                              help="Gerçek kullanımda 240 (4 dakika), test için 5 girebilirsin")
    st.markdown("---")
    st.info("💡 Test için beklemeyi 5 saniyeye düşür")

# ========== EXCEL YÜKLEME ==========
st.subheader("📁 E-Posta Listesi")

col1, col2 = st.columns(2)
with col1:
    uploaded = st.file_uploader("Excel dosyası yükle (.xlsx)", type=["xlsx"])
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📥 Şablon İndir"):
        ornek = pd.DataFrame({
            "Alıcı E-posta": ["ornek@mail.com", "diger@mail.com"],
            "Konu": ["Konu 1", "Konu 2"],
            "İçerik": ["E-posta içeriği 1", "E-posta içeriği 2"]
        })
        st.download_button("💾 İndir", ornek.to_csv(index=False).encode("utf-8"),
                           "eposta_sablonu.csv", "text/csv")

if uploaded:
    df = pd.read_excel(uploaded)
    st.success(f"✅ {len(df)} e-posta yüklendi")
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("🚀 Gönderim")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📨 Toplam", len(df))
    with col2:
        sure_dk = (len(df) * aralik) // 60
        sure_sn = (len(df) * aralik) % 60
        st.metric("⏱️ Süre", f"{sure_dk}dk {sure_sn}sn")
    with col3:
        simdi = datetime.now().strftime("%H:%M")
        st.metric("🕐 Şu an", simdi)

    st.markdown("")

    if st.button("▶️ GÖNDERMEYE BAŞLA", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_box = st.empty()
        log_box = st.empty()
        logs = []

        basarili = 0
        hatali = 0

        for i, satir in df.iterrows():
            alici = satir["Alıcı E-posta"]
            konu = satir["Konu"]
            icerik = satir["İçerik"]

            status_box.info(f"📤 Gönderiliyor: [{i+1}/{len(df)}] → {alici}")

            try:
                msg = MIMEMultipart()
                msg["From"] = email_user
                msg["To"] = alici
                msg["Subject"] = konu
                msg.attach(MIMEText(icerik, "plain", "utf-8"))

                server = smtplib.SMTP(smtp_server, int(smtp_port), timeout=15)
                server.ehlo()
                server.starttls()
                server.login(email_user, email_pass)
                server.sendmail(email_user, alici, msg.as_string())
                server.quit()

                basarili += 1
                logs.append(f"✅ [{i+1}/{len(df)}] {alici} → Gönderildi ({datetime.now().strftime('%H:%M:%S')})")

            except Exception as e:
                hatali += 1
                logs.append(f"❌ [{i+1}/{len(df)}] {alici} → Hata: {str(e)}")

            progress_bar.progress((i + 1) / len(df))
            log_box.code("\n".join(logs[-10:]))  # Son 10 logu göster

            if i < len(df) - 1:
                for kalan in range(int(aralik), 0, -1):
                    status_box.info(f"⏳ Sonraki e-posta: {kalan} saniye sonra... [{i+2}/{len(df)}]")
                    time.sleep(1)

        status_box.empty()
        if hatali == 0:
            st.success(f"🎉 Tamamlandı! {basarili} e-posta başarıyla gönderildi.")
        else:
            st.warning(f"⚠️ {basarili} başarılı, {hatali} hatalı")

        st.code("\n".join(logs))

else:
    st.info("👆 Excel dosyasını yükleyerek başla")
    st.markdown("""
    ### Excel formatı:
    | Alıcı E-posta | Konu | İçerik |
    |---|---|---|
    | ali@mail.com | Merhaba | E-posta içeriği... |
    | veli@mail.com | Teklif | İçerik... |
    """)
