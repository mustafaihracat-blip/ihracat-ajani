import streamlit as st
import pandas as pd
import smtplib
import time
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

st.set_page_config(page_title="📧 E-Posta Yöneticisi", page_icon="📧", layout="centered")

# ========== SIDEBAR - SMTP ==========
with st.sidebar:
    st.header("⚙️ SMTP Ayarları")
    smtp_server = st.text_input("SMTP Sunucu", value="mail.kursdegilkariyer.online")
    smtp_port   = st.number_input("Port", value=587, step=1)
    email_user  = st.text_input("Gönderen E-posta", value="bilgi@kursdegilkariyer.online")
    email_pass  = st.text_input("Şifre", value="Mustafa1234", type="password")
    aralik      = st.number_input("E-postalar arası bekleme (sn)", value=240, step=10,
                                   help="Test: 5 sn | Gerçek: 240 sn (4 dk)")
    st.markdown("---")
    st.caption("💡 Test için beklemeyi 5 sn yap")

# ========== ADIM GÖSTERGESI ==========
os.makedirs("kampanyalar", exist_ok=True)
os.makedirs("sablonlar", exist_ok=True)
os.makedirs("listeler", exist_ok=True)

if "adim" not in st.session_state:
    st.session_state.adim = 1
if "kampanya" not in st.session_state:
    st.session_state.kampanya = {}

def adim_goster():
    adimlar = ["1️⃣ Tanımla", "2️⃣ Şablon", "3️⃣ Alıcılar", "4️⃣ Gönder"]
    cols = st.columns(4)
    for i, (col, ad) in enumerate(zip(cols, adimlar), 1):
        with col:
            if i == st.session_state.adim:
                st.markdown(f"<div style=\"background:#2563eb;color:white;padding:10px;border-radius:8px;text-align:center;font-weight:bold;\">{ad}</div>", unsafe_allow_html=True)
            elif i < st.session_state.adim:
                st.markdown(f"<div style=\"background:#bbf7d0;color:#166534;padding:10px;border-radius:8px;text-align:center;\">✅ {ad}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style=\"background:#f1f5f9;color:#94a3b8;padding:10px;border-radius:8px;text-align:center;\">{ad}</div>", unsafe_allow_html=True)

adim_goster()
st.markdown("---")

# ========== ADIM 1: TANIMI ==========
if st.session_state.adim == 1:
    st.subheader("1️⃣ Kampanyayı Tanımla")
    
    kampanya_adi = st.text_input("📌 Kampanya Adı", 
                                  value=st.session_state.kampanya.get("ad", ""),
                                  placeholder="Örn: Dis_Ticaret_Mart_2025")
    konu = st.text_input("✉️ E-posta Konusu",
                          value=st.session_state.kampanya.get("konu", ""),
                          placeholder="Örn: 🎓 Dış Ticaret Eğitim Programı")
    gonderen_ad = st.text_input("👤 Gönderen Adı",
                                 value=st.session_state.kampanya.get("gonderen_ad", "Kurs Değil Kariyer"),
                                 placeholder="Örn: Mustafa Hoca")

    if st.button("İleri ➡️", type="primary", use_container_width=True):
        if kampanya_adi and konu:
            st.session_state.kampanya = {
                "ad": kampanya_adi,
                "konu": konu,
                "gonderen_ad": gonderen_ad
            }
            os.makedirs(f"kampanyalar/{kampanya_adi}", exist_ok=True)
            st.session_state.adim = 2
            st.rerun()
        else:
            st.error("❌ Kampanya adı ve konu zorunludur!")

# ========== ADIM 2: ŞABLON ==========
elif st.session_state.adim == 2:
    st.subheader("2️⃣ E-Posta Şablonu Seç")

    # Mevcut şablonlar
    mevcut = [f for f in os.listdir("sablonlar") if f.endswith(".html")]
    
    secim = st.radio("Şablon kaynağı:", 
                      ["📁 Mevcut şablon kullan", "⬆️ Yeni şablon yükle"],
                      horizontal=True)

    if secim == "📁 Mevcut şablon kullan":
        if mevcut:
            secili_sablon = st.selectbox("Şablon seç:", mevcut)
            sablon_yolu = f"sablonlar/{secili_sablon}"
            with open(sablon_yolu, "r", encoding="utf-8") as f:
                html_onizleme = f.read()
            with st.expander("👁️ Şablonu Önizle"):
                st.components.v1.html(html_onizleme, height=500, scrolling=True)
            st.session_state.kampanya["sablon"] = sablon_yolu
        else:
            st.warning("⚠️ Kayıtlı şablon yok. Yeni şablon yükle!")

    else:
        sablon_file = st.file_uploader("HTML Şablon Yükle", type=["html"])
        sablon_adi  = st.text_input("Şablon adı", placeholder="Örn: dis_ticaret_sablon.html")
        
        if sablon_file and sablon_adi:
            if not sablon_adi.endswith(".html"):
                sablon_adi += ".html"
            icerik = sablon_file.read().decode("utf-8")
            sablon_yolu = f"sablonlar/{sablon_adi}"
            with open(sablon_yolu, "w", encoding="utf-8") as f:
                f.write(icerik)
            st.success(f"✅ '{sablon_adi}' kaydedildi!")
            with st.expander("👁️ Önizle"):
                st.components.v1.html(icerik, height=500, scrolling=True)
            st.session_state.kampanya["sablon"] = sablon_yolu

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Geri", use_container_width=True):
            st.session_state.adim = 1
            st.rerun()
    with col2:
        if st.button("İleri ➡️", type="primary", use_container_width=True):
            if "sablon" in st.session_state.kampanya:
                st.session_state.adim = 3
                st.rerun()
            else:
                st.error("❌ Önce bir şablon seç veya yükle!")

# ========== ADIM 3: ALİCİLAR ==========
elif st.session_state.adim == 3:
    st.subheader("3️⃣ Alıcı Listesi Seç")

    mevcut_listeler = [f for f in os.listdir("listeler") if f.endswith(".xlsx")]

    secim = st.radio("Liste kaynağı:",
                      ["📁 Mevcut liste kullan", "⬆️ Yeni liste yükle"],
                      horizontal=True)

    if secim == "📁 Mevcut liste kullan":
        if mevcut_listeler:
            secili_liste = st.selectbox("Liste seç:", mevcut_listeler)
            liste_yolu = f"listeler/{secili_liste}"
            df = pd.read_excel(liste_yolu)
            st.success(f"✅ {len(df)} alıcı")
            st.dataframe(df, use_container_width=True, height=200)
            st.session_state.kampanya["liste"] = liste_yolu
        else:
            st.warning("⚠️ Kayıtlı liste yok. Yeni liste yükle!")
    else:
        liste_file = st.file_uploader("Excel Listesi (.xlsx)", type=["xlsx"])
        liste_adi  = st.text_input("Liste adı", placeholder="Örn: mart_listesi")

        if liste_file and liste_adi:
            if not liste_adi.endswith(".xlsx"):
                liste_adi += ".xlsx"
            df_upload = pd.read_excel(liste_file)
            liste_yolu = f"listeler/{liste_adi}"
            df_upload.to_excel(liste_yolu, index=False)
            st.success(f"✅ {len(df_upload)} alıcı kaydedildi!")
            st.dataframe(df_upload, use_container_width=True, height=200)
            st.session_state.kampanya["liste"] = liste_yolu

        # Boş şablon indir
        ornek = pd.DataFrame({"Alıcı E-posta": ["ali@mail.com", "veli@mail.com"]})
        st.download_button("📥 Boş Excel Şablonu İndir",
                           ornek.to_csv(index=False).encode("utf-8"),
                           "alici_sablonu.csv", "text/csv")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Geri", use_container_width=True):
            st.session_state.adim = 2
            st.rerun()
    with col2:
        if st.button("İleri ➡️", type="primary", use_container_width=True):
            if "liste" in st.session_state.kampanya:
                st.session_state.adim = 4
                st.rerun()
            else:
                st.error("❌ Önce bir liste seç veya yükle!")

# ========== ADIM 4: GÖNDER ==========
elif st.session_state.adim == 4:
    st.subheader("4️⃣ Özet & Gönder")

    k = st.session_state.kampanya
    df = pd.read_excel(k["liste"])

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📌 **Kampanya:** {k['ad']}")
        st.info(f"✉️ **Konu:** {k['konu']}")
        st.info(f"👤 **Gönderen:** {k['gonderen_ad']}")
    with col2:
        st.info(f"🎨 **Şablon:** {os.path.basename(k['sablon'])}")
        st.info(f"📋 **Liste:** {os.path.basename(k['liste'])}")
        st.info(f"📨 **Toplam Alıcı:** {len(df)}")

    sure = (len(df) * int(aralik)) // 60
    st.warning(f"⏱️ Tahmini süre: **~{sure} dakika** ({len(df)} e-posta × {aralik} sn)")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Geri", use_container_width=True):
            st.session_state.adim = 3
            st.rerun()
    with col2:
        gonder = st.button("🚀 GÖNDERMEYE BAŞLA", type="primary", use_container_width=True)

    if gonder:
        with open(k["sablon"], "r", encoding="utf-8") as f:
            html_sablon = f.read()

        progress_bar = st.progress(0)
        status_box   = st.empty()
        log_box      = st.empty()
        logs = []
        basarili = hatali = 0

        for i, satir in df.iterrows():
            alici = satir["Alıcı E-posta"]
            html  = html_sablon.replace("{{AD_SOYAD}}", "Yetkili")
            html  = html.replace("Sayın <strong>Yetkili</strong>", "Sayın Yetkili")

            status_box.info(f"📤 [{i+1}/{len(df)}] → {alici}")
            try:
                msg = MIMEMultipart("alternative")
                msg["From"]    = f"{k['gonderen_ad']} <{email_user}>"
                msg["To"]      = alici
                msg["Subject"] = k["konu"]
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

        if st.button("🔄 Yeni Kampanya Başlat"):
            st.session_state.adim = 1
            st.session_state.kampanya = {}
            st.rerun()
