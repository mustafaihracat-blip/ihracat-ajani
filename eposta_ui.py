import streamlit as st
import pandas as pd
import smtplib
import time
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

st.set_page_config(page_title="📧 E-Posta Gönderici", page_icon="📧", layout="centered")
st.title("📧 Otomatik E-Posta Gönderici")
st.markdown("---")

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("⚙️ SMTP Ayarları")
    smtp_server = st.text_input("SMTP Sunucu", value="mail.kursdegilkariyer.online")
    smtp_port = st.number_input("Port", value=587, step=1)
    email_user = st.text_input("E-posta", value="bilgi@kursdegilkariyer.online")
    email_pass = st.text_input("Şifre", value="Mustafa1234", type="password")
    aralik = st.number_input("Bekleme süresi (saniye)", value=240, step=10,
                              help="Test: 5 sn | Gerçek: 240 sn (4 dk)")
    st.markdown("---")
    st.info("💡 Test için beklemeyi 5 saniyeye düşür")

# ========== ŞABLON YÜKLEMESİ ==========
SABLON_PATH = "eposta_sablon.html"

st.subheader("🎨 E-Posta Şablonu")

col1, col2 = st.columns(2)
with col1:
    sablon_file = st.file_uploader("HTML Şablon Yükle", type=["html"], 
                                    help="eposta_sablon.html dosyasını yükle")
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if os.path.exists(SABLON_PATH):
        st.success("✅ Şablon yüklü")
    else:
        st.warning("⚠️ Şablon bulunamadı")

if sablon_file:
    sablon_icerik = sablon_file.read().decode("utf-8")
    with open(SABLON_PATH, "w", encoding="utf-8") as f:
        f.write(sablon_icerik)
    st.success("✅ Yeni şablon kaydedildi!")
    with st.expander("👁️ Şablon Önizleme"):
        st.components.v1.html(sablon_icerik, height=600, scrolling=True)
elif os.path.exists(SABLON_PATH):
    with open(SABLON_PATH, "r", encoding="utf-8") as f:
        sablon_icerik = f.read()
    with st.expander("👁️ Mevcut Şablonu Önizle"):
        st.components.v1.html(sablon_icerik, height=600, scrolling=True)

st.markdown("---")

# ========== EXCEL ==========
st.subheader("📁 Alıcı Listesi")

col1, col2 = st.columns(2)
with col1:
    uploaded = st.file_uploader("Excel dosyası (.xlsx)", type=["xlsx"])
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    ornek = pd.DataFrame({"Alıcı E-posta": ["ali@mail.com", "veli@mail.com"]})
    st.download_button("📥 Şablon İndir", 
                       ornek.to_csv(index=False).encode("utf-8"),
                       "alici_listesi.csv", "text/csv")

if uploaded:
    df = pd.read_excel(uploaded)
    st.success(f"✅ {len(df)} alıcı yüklendi")
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("🚀 Gönderim")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📨 Toplam Alıcı", len(df))
    with col2:
        sure = (len(df) * aralik) // 60
        st.metric("⏱️ Toplam Süre", f"~{sure} dk")
    with col3:
        st.metric("🕐 Şu an", datetime.now().strftime("%H:%M"))

    konu = st.text_input("📌 E-posta Konusu", 
                          value="🎓 Dış Ticaret Eğitim Programı | Eğitim Al + İşe Yerleş + Sonra Öde")

    if st.button("▶️ GÖNDERMEYE BAŞLA", type="primary", use_container_width=True):
        if not os.path.exists(SABLON_PATH):
            st.error("❌ Önce HTML şablonu yükleyin!")
        else:
            with open(SABLON_PATH, "r", encoding="utf-8") as f:
                html_sablon = f.read()

            progress_bar = st.progress(0)
            status_box = st.empty()
            log_box = st.empty()
            logs = []
            basarili = hatali = 0

            for i, satir in df.iterrows():
                alici = satir["Alıcı E-posta"]
                html = html_sablon.replace("{{AD_SOYAD}}", "Yetkili")
                html = html.replace("Sayın <strong>Yetkili</strong>", "Sayın Yetkili")

                status_box.info(f"📤 [{i+1}/{len(df)}] Gönderiliyor → {alici}")
                try:
                    msg = MIMEMultipart("alternative")
                    msg["From"] = f"Kurs Değil Kariyer <{email_user}>"
                    msg["To"] = alici
                    msg["Subject"] = konu
                    msg.attach(MIMEText("HTML e-posta istemcisi kullanın.", "plain", "utf-8"))
                    msg.attach(MIMEText(html, "html", "utf-8"))

                    server = smtplib.SMTP(smtp_server, int(smtp_port), timeout=15)
                    server.ehlo()
                    server.starttls()
                    server.login(email_user, email_pass)
                    server.sendmail(email_user, alici, msg.as_string())
                    server.quit()

                    basarili += 1
                    logs.append(f"✅ [{i+1}/{len(df)}] {alici} → {datetime.now().strftime('%H:%M:%S')}")
                except Exception as e:
                    hatali += 1
                    logs.append(f"❌ [{i+1}/{len(df)}] {alici} → Hata: {str(e)}")

                progress_bar.progress((i+1)/len(df))
                log_box.code("\n".join(logs[-10:]))

                if i < len(df)-1:
                    for kalan in range(int(aralik), 0, -1):
                        status_box.info(f"⏳ Sonraki: {kalan}sn sonra... [{i+2}/{len(df)}]")
                        time.sleep(1)

            status_box.empty()
            if hatali == 0:
                st.success(f"🎉 Tamamlandı! {basarili} e-posta gönderildi.")
            else:
                st.warning(f"⚠️ {basarili} başarılı | {hatali} hatalı")
            st.code("\n".join(logs))
else:
    st.info("👆 Excel dosyasını yükleyerek başla — sadece 'Alıcı E-posta' sütunu yeterli!")
