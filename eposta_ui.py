import streamlit as st
import pandas as pd
import smtplib
import time
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

st.set_page_config(page_title="📧 E-Posta Yöneticisi", page_icon="📧", layout="centered")

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("⚙️ SMTP Ayarları")
    smtp_server = st.text_input("SMTP Sunucu", value="mail.kursdegilkariyer.online")
    smtp_port   = st.number_input("Port", value=587, step=1)
    email_user  = st.text_input("Gönderen E-posta", value="bilgi@kursdegilkariyer.online")
    email_pass  = st.text_input("Şifre", value="Mustafa1234", type="password")
    aralik      = st.number_input("Bekleme (sn)", value=240, step=10, help="Test: 5 sn | Gerçek: 240 sn")
    st.caption("💡 Test için beklemeyi 5 sn yap")

# ========== KLASÖRLER ==========
for klasor in ["sablonlar", "listeler"]:
    os.makedirs(klasor, exist_ok=True)

# ========== SESSION STATE ==========
if "adim" not in st.session_state:
    st.session_state.adim = 1
if "kampanya" not in st.session_state:
    st.session_state.kampanya = {}

# ========== ADIM GÖSTERGESI ==========
def adim_goster():
    adimlar = ["1️⃣ Tanımla", "2️⃣ Şablon", "3️⃣ Alıcılar", "4️⃣ Gönder"]
    cols = st.columns(4)
    for i, (col, ad) in enumerate(zip(cols, adimlar), 1):
        with col:
            if i == st.session_state.adim:
                st.markdown(f'<div style="background:#2563eb;color:white;padding:10px;border-radius:8px;text-align:center;font-weight:bold;">{ad}</div>', unsafe_allow_html=True)
            elif i < st.session_state.adim:
                st.markdown(f'<div style="background:#bbf7d0;color:#166534;padding:10px;border-radius:8px;text-align:center;">✅ {ad}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="background:#f1f5f9;color:#94a3b8;padding:10px;border-radius:8px;text-align:center;">{ad}</div>', unsafe_allow_html=True)

adim_goster()
st.markdown("---")

# ========== ADIM 1: TANIMI ==========
if st.session_state.adim == 1:
    st.subheader("1️⃣ Kampanyayı Tanımla")
    kampanya_adi = st.text_input("📌 Kampanya Adı", value=st.session_state.kampanya.get("ad",""), placeholder="Örn: Mart_2025")
    konu         = st.text_input("✉️ E-posta Konusu", value=st.session_state.kampanya.get("konu",""), placeholder="Örn: 🎓 Dış Ticaret Eğitim Programı")
    gonderen_ad  = st.text_input("👤 Gönderen Adı", value=st.session_state.kampanya.get("gonderen_ad","Kurs Değil Kariyer"))

    if st.button("İleri ➡️", type="primary", use_container_width=True):
        if kampanya_adi and konu:
            st.session_state.kampanya = {"ad": kampanya_adi, "konu": konu, "gonderen_ad": gonderen_ad}
            st.session_state.adim = 2
            st.rerun()
        else:
            st.error("❌ Kampanya adı ve konu zorunludur!")

# ========== ADIM 2: ŞABLON ==========
elif st.session_state.adim == 2:
    st.subheader("2️⃣ E-Posta Şablonu Seç")

    mevcut = [f for f in os.listdir("sablonlar") if f.endswith(".html")]
    secim  = st.radio("Şablon kaynağı:", ["📁 Mevcut şablon kullan", "⬆️ Yeni şablon yükle"], horizontal=True)

    if secim == "📁 Mevcut şablon kullan":
        if mevcut:
            secili = st.selectbox("Şablon seç:", mevcut)
            yol = f"sablonlar/{secili}"
            with open(yol, "r", encoding="utf-8") as f:
                html = f.read()
            with st.expander("👁️ Önizle"):
                st.components.v1.html(html, height=500, scrolling=True)
            st.session_state.kampanya["sablon"] = yol
        else:
            st.warning("⚠️ Kayıtlı şablon yok, yeni yükle!")
    else:
        sablon_file = st.file_uploader("HTML Şablon Yükle", type=["html"])
        sablon_adi  = st.text_input("Şablon adı", placeholder="Örn: dis_ticaret.html")
        if sablon_file and sablon_adi:
            if not sablon_adi.endswith(".html"):
                sablon_adi += ".html"
            icerik = sablon_file.read().decode("utf-8")
            yol = f"sablonlar/{sablon_adi}"
            with open(yol, "w", encoding="utf-8") as f:
                f.write(icerik)
            st.success(f"✅ '{sablon_adi}' kaydedildi!")
            with st.expander("👁️ Önizle"):
                st.components.v1.html(icerik, height=500, scrolling=True)
            st.session_state.kampanya["sablon"] = yol

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Geri", use_container_width=True):
            st.session_state.adim = 1; st.rerun()
    with col2:
        if st.button("İleri ➡️", type="primary", use_container_width=True):
            if "sablon" in st.session_state.kampanya:
                st.session_state.adim = 3; st.rerun()
            else:
                st.error("❌ Önce şablon seç!")

# ========== ADIM 3: ALİCİLAR ==========
elif st.session_state.adim == 3:
    st.subheader("3️⃣ Alıcı Listesi Seç")

    mevcut_listeler = [f for f in os.listdir("listeler") if f.endswith(".xlsx")]
    secim = st.radio("Liste kaynağı:", ["📁 Mevcut liste kullan", "⬆️ Yeni liste yükle"], horizontal=True)

    if secim == "📁 Mevcut liste kullan":
        if mevcut_listeler:
            secili = st.selectbox("Liste seç:", mevcut_listeler)
            yol = f"listeler/{secili}"
            df  = pd.read_excel(yol)
            st.success(f"✅ {len(df)} alıcı | Sütunlar: {list(df.columns)}")
            st.dataframe(df, use_container_width=True, height=200)
            st.session_state.kampanya["liste"] = yol
        else:
            st.warning("⚠️ Kayıtlı liste yok, yeni yükle!")
    else:
        liste_file = st.file_uploader("Excel Listesi (.xlsx)", type=["xlsx"])
        liste_adi  = st.text_input("Liste adı", placeholder="Örn: mart_listesi")
        if liste_file and liste_adi:
            if not liste_adi.endswith(".xlsx"):
                liste_adi += ".xlsx"
            df_u = pd.read_excel(liste_file)
            yol  = f"listeler/{liste_adi}"
            df_u.to_excel(yol, index=False)
            st.success(f"✅ {len(df_u)} alıcı kaydedildi! Sütunlar: {list(df_u.columns)}")
            st.dataframe(df_u, use_container_width=True, height=200)
            st.session_state.kampanya["liste"] = yol

        ornek = pd.DataFrame({"E-posta": ["ali@mail.com", "veli@mail.com"]})
        st.download_button("📥 Boş Şablon İndir", ornek.to_csv(index=False).encode("utf-8"), "liste.csv", "text/csv")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Geri", use_container_width=True):
            st.session_state.adim = 2; st.rerun()
    with col2:
        if st.button("İleri ➡️", type="primary", use_container_width=True):
            if "liste" in st.session_state.kampanya:
                st.session_state.adim = 4; st.rerun()
            else:
                st.error("❌ Önce liste seç!")

# ========== ADIM 4: GÖNDER ==========
elif st.session_state.adim == 4:
    st.subheader("4️⃣ Özet & Gönder")

    k  = st.session_state.kampanya
    df = pd.read_excel(k["liste"])

    # E-posta sütununu otomatik bul
    email_sutun = None
    for col in df.columns:
        if any(k2 in col.lower() for k2 in ["posta", "mail", "email"]):
            email_sutun = col
            break
    if email_sutun is None:
        email_sutun = df.columns[0]  # Bulamazsa ilk sütunu kullan

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📌 **Kampanya:** {k['ad']}")
        st.info(f"✉️ **Konu:** {k['konu']}")
        st.info(f"👤 **Gönderen:** {k['gonderen_ad']}")
    with col2:
        st.info(f"🎨 **Şablon:** {os.path.basename(k['sablon'])}")
        st.info(f"📋 **Liste:** {os.path.basename(k['liste'])}")
        st.info(f"📨 **Alıcı:** {len(df)} kişi → '{email_sutun}' sütunu")

    sure = (len(df) * int(aralik)) // 60
    st.warning(f"⏱️ Tahmini süre: **~{sure} dakika**")

    konu_goster = st.text_input("✉️ Konu (düzenle):", value=k["konu"])

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Geri", use_container_width=True):
            st.session_state.adim = 3; st.rerun()
    with col2:
        gonder = st.button("🚀 GÖNDERMEYE BAŞLA", type="primary", use_container_width=True)

    if gonder:
        with open(k["sablon"], "r", encoding="utf-8") as f:
            html_sablon = f.read()

        progress_bar = st.progress(0)
        status_box   = st.empty()
        log_box      = st.empty()
        logs         = []
        basarili = hatali = 0

        for i, satir in df.iterrows():
            alici = str(satir[email_sutun]).strip()
            html  = html_sablon.replace("{{AD_SOYAD}}", "Yetkili")
            html  = html.replace("Sayın <strong>Yetkili</strong>", "Sayın Yetkili")

            status_box.info(f"📤 [{i+1}/{len(df)}] → {alici}")
            try:
                msg = MIMEMultipart("alternative")
                msg["From"]    = f"{k['gonderen_ad']} <{email_user}>"
                msg["To"]      = alici
                msg["Subject"] = konu_goster
                msg.attach(MIMEText("HTML e-posta istemcisi kullanın.", "plain", "utf-8"))
                msg.attach(MIMEText(html, "html", "utf-8"))

                server = smtplib.SMTP(smtp_server, int(smtp_port), timeout=15)
                server.ehlo(); server.starttls()
                server.login(email_user, email_pass)
                server.sendmail(email_user, alici, msg.as_string())
                server.quit()

                basarili += 1
                logs.append(f"✅ [{i+1}/{len(df)}] {alici} → {datetime.now().strftime('%H:%M:%S')}")
            except Exception as e:
                hatali += 1
                logs.append(f"❌ [{i+1}/{len(df)}] {alici} → {str(e)}")

            progress_bar.progress((i+1)/len(df))
            log_box.code("\n".join(logs[-10:]))

            if i < len(df)-1:
                for kalan in range(int(aralik), 0, -1):
                    status_box.info(f"⏳ Sonraki: {kalan}sn... [{i+2}/{len(df)}]")
                    time.sleep(1)

        status_box.empty()
        if hatali == 0:
            st.success(f"🎉 Tamamlandı! {basarili} e-posta gönderildi.")
        else:
            st.warning(f"⚠️ {basarili} başarılı | {hatali} hatalı")
        st.code("\n".join(logs))

        if st.button("🔄 Yeni Kampanya"):
            st.session_state.adim = 1
            st.session_state.kampanya = {}
            st.rerun()
