import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import io
import json

# ─── SAYFA AYARLARI ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OSB Evrensel Firma Tarayıcı",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; }
    .hero-box {
        background: linear-gradient(135deg, #1e3a5f, #2e86de);
        border-radius: 16px; padding: 2rem 2.5rem;
        color: white; margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    .hero-box h1 { font-size: 2rem; margin: 0; }
    .hero-box p  { font-size: 1rem; margin: 0.5rem 0 0; opacity: 0.85; }
    .card {
        background: white; border-radius: 12px;
        padding: 1.5rem; box-shadow: 0 2px 10px rgba(0,0,0,0.07);
        margin-bottom: 1.2rem;
    }
    .stat-box {
        background: white; border-radius: 12px;
        padding: 1.2rem 1rem; text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.07);
    }
    .stat-number { font-size: 2rem; font-weight: 700; color: #2e86de; }
    .stat-label  { font-size: 0.82rem; color: #666; margin-top: 4px; }
    .stButton > button {
        background: linear-gradient(135deg, #2e86de, #1e3a5f);
        color: white; border: none; border-radius: 8px;
        padding: 0.6rem 1.5rem; font-weight: 600; width: 100%;
    }
    .stButton > button:hover { opacity: 0.88; color: white; }
    .log-box {
        background: #1e1e2e; color: #a6e3a1; border-radius: 8px;
        padding: 1rem; font-family: monospace; font-size: 0.82rem;
        max-height: 200px; overflow-y: auto;
    }
    .strateji-badge {
        display: inline-block; background: #d4edda; color: #155724;
        border-radius: 20px; padding: 2px 10px; font-size: 0.78rem; font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ─── YARDIMCI FONKSİYONLAR ────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def temizle(metin):
    return re.sub(r"\s+", " ", str(metin)).strip()

def email_bul(metin):
    eslesmeler = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", str(metin))
    return eslesmeler[0] if eslesmeler else ""

def tel_bul(metin):
    eslesmeler = re.findall(r"[\+\(]?[\d][\d\s\-\.\(\)]{7,}[\d]", str(metin))
    return eslesmeler[0].strip() if eslesmeler else ""

def url_bul(metin):
    eslesmeler = re.findall(r"https?://[^\s"'<>]+", str(metin))
    return eslesmeler[0] if eslesmeler else ""

# ─── STRATEJI 1: TABLO TARAMA ─────────────────────────────────────────────────
def strateji_tablo(soup):
    firmalar = []
    for tablo in soup.select("table"):
        satirlar = tablo.select("tr")
        if len(satirlar) < 2:
            continue
        basliklar = [temizle(th.get_text()) for th in satirlar[0].select("th, td")]
        for satir in satirlar[1:]:
            hucreler = [temizle(td.get_text()) for td in satir.select("td")]
            if not hucreler or not hucreler[0]:
                continue
            firma = {}
            if basliklar:
                for i, baslik in enumerate(basliklar):
                    firma[baslik if baslik else f"Alan{i+1}"] = hucreler[i] if i < len(hucreler) else ""
            else:
                firma["Firma Adı"] = hucreler[0]
                firma["Sektör"]   = hucreler[1] if len(hucreler) > 1 else ""
                firma["Telefon"]  = hucreler[2] if len(hucreler) > 2 else ""
                firma["E-posta"]  = hucreler[3] if len(hucreler) > 3 else ""
                firma["Adres"]    = hucreler[4] if len(hucreler) > 4 else ""
            firmalar.append(firma)
    return firmalar

# ─── STRATEJI 2: KART / LİSTE TARAMA ─────────────────────────────────────────
KART_SELECTORS = [
    ".firma", ".company", ".member", ".uye", ".uye-firma",
    ".card", ".liste-item", ".item", "article", ".post",
    "[class*=firma]", "[class*=company]", "[class*=member]",
    "[class*=uye]", "[class*=card]"
]

def strateji_kart(soup, html_str):
    firmalar = []
    for sel in KART_SELECTORS:
        kartlar = soup.select(sel)
        if len(kartlar) < 3:
            continue
        for kart in kartlar:
            tam_metin = kart.get_text(" | ", strip=True)
            if len(tam_metin) < 5:
                continue
            baslik = kart.select_one("h1,h2,h3,h4,h5,strong,b,a")
            firma = {
                "Firma Adı": temizle(baslik.get_text()) if baslik else tam_metin[:60],
                "E-posta":   email_bul(str(kart)),
                "Telefon":   tel_bul(tam_metin),
                "Web Sitesi":url_bul(str(kart)),
                "Ham Metin": tam_metin[:200],
            }
            if firma["Firma Adı"]:
                firmalar.append(firma)
        if firmalar:
            return firmalar
    return firmalar

# ─── STRATEJI 3: AKILLİ REGEX TARAMA ─────────────────────────────────────────
def strateji_regex(html_str):
    """Tüm HTML üzerinde e-posta, telefon ve çevre metni toplar"""
    firmalar = []
    soup = BeautifulSoup(html_str, "html.parser")
    
    # Tüm bağlantılı elementleri tara
    for a in soup.select("a[href^=mailto]"):
        eposta = a["href"].replace("mailto:", "").split("?")[0].strip()
        ebeveyn = a.find_parent(["li", "div", "tr", "td", "section", "article"])
        metin   = temizle(ebeveyn.get_text()) if ebeveyn else temizle(a.get_text())
        firmalar.append({
            "Firma Adı": metin[:80] if metin else eposta,
            "E-posta":   eposta,
            "Telefon":   tel_bul(metin),
            "Ham Metin": metin[:200],
        })
    return firmalar

# ─── SAYFA LİNKLERİ BUL ──────────────────────────────────────────────────────
def sonraki_sayfalar_bul(soup, base_url):
    """Sayfalama linklerini bulur"""
    linkler = set()
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        metin = temizle(a.get_text()).lower()
        # Sayfa numaraları veya "ileri" linkleri
        if re.search(r"page[=\/]\d+|sayfa\d+|\bpage\b|sonraki|ileri|next|>", metin + href, re.I):
            if href.startswith("http"):
                linkler.add(href)
            elif href.startswith("/"):
                linkler.add(base_url.rstrip("/") + href)
    return list(linkler)[:10]

# ─── ANA TARAMA FONKSİYONU ────────────────────────────────────────────────────
def osb_universal_tara(url, max_sayfa=20, gecikme=0.5):
    tum_firmalar = []
    loglar = []
    ziyaret_edildi = set()
    kuyruk = [url]
    sayfa_no = 0

    while kuyruk and sayfa_no < max_sayfa:
        mevcut_url = kuyruk.pop(0)
        if mevcut_url in ziyaret_edildi:
            continue
        ziyaret_edildi.add(mevcut_url)
        sayfa_no += 1

        try:
            resp = requests.get(mevcut_url, headers=HEADERS, timeout=15)
            resp.encoding = resp.apparent_encoding
            resp.raise_for_status()
        except Exception as e:
            loglar.append(f"❌ Sayfa {sayfa_no}: {e}")
            continue

        soup     = BeautifulSoup(resp.text, "html.parser")
        html_str = resp.text

        # Stratejileri sırayla dene
        firmalar = strateji_tablo(soup)
        if firmalar:
            loglar.append(f"✅ Sayfa {sayfa_no} — Tablo stratejisi → {len(firmalar)} firma")
        else:
            firmalar = strateji_kart(soup, html_str)
            if firmalar:
                loglar.append(f"✅ Sayfa {sayfa_no} — Kart stratejisi → {len(firmalar)} firma")
            else:
                firmalar = strateji_regex(html_str)
                if firmalar:
                    loglar.append(f"✅ Sayfa {sayfa_no} — Regex stratejisi → {len(firmalar)} firma")
                else:
                    loglar.append(f"⚠️ Sayfa {sayfa_no} — Veri bulunamadı")

        # Kaynak URL ekle
        for f in firmalar:
            f["Kaynak"] = mevcut_url

        tum_firmalar.extend(firmalar)

        # Sonraki sayfaları kuyruğa ekle (sadece ilk sayfada)
        if sayfa_no == 1:
            yeni_sayfalar = sonraki_sayfalar_bul(soup, url)
            for yeni in yeni_sayfalar:
                if yeni not in ziyaret_edildi:
                    kuyruk.append(yeni)
            if yeni_sayfalar:
                loglar.append(f"🔗 {len(yeni_sayfalar)} sayfa daha bulundu")

        time.sleep(gecikme)

    # Mükerrer temizle
    df = pd.DataFrame(tum_firmalar).drop_duplicates()
    return df, loglar

# ─── SESSION STATE ────────────────────────────────────────────────────────────
for key in ["df_firmalar", "loglar", "tarama_bitti"]:
    if key not in st.session_state:
        st.session_state[key] = None if key == "df_firmalar" else ([] if key == "loglar" else False)

# ─── HERO ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-box">
    <h1>🏭 OSB Evrensel Firma Tarayıcı</h1>
    <p>Her OSB sitesini otomatik analiz eder • Tablo, Kart, Regex stratejileri • Sayfalama desteği</p>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Tarama Ayarları")
    st.markdown("---")
    max_sayfa  = st.slider("Maksimum Sayfa", 1, 50, 10)
    gecikme    = st.select_slider("İstek Gecikmesi (san)", [0.2, 0.5, 1.0, 2.0], value=0.5)
    st.markdown("---")
    st.markdown("### 📌 Stratejiler")
    st.success("✅ Tablo Tarama")
    st.info("🟦 Kart/Liste Tarama")
    st.warning("🟡 Regex / E-posta Tarama")
    st.markdown("---")
    st.caption("Her OSB sitesinde sırayla denenir. İlk bulan strateji kullanılır.")

# ─── ÇOKLU URL GİRİŞİ ────────────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### 🔗 OSB Web Sitesi / Siteleri")
st.caption("Birden fazla OSB girebilirsin — her satıra bir URL")
url_girisi = st.text_area(
    label="",
    placeholder="https://www.iosb.org.tr/uyefirmalar\nhttps://www.bosb.org.tr/firmalar\nhttps://www.aosb.org.tr/uyeler",
    height=100,
    label_visibility="collapsed"
)
osb_adi = st.text_input("Kayıt Adı (dosya adı için)", placeholder="istanbul_osb")
col1, col2 = st.columns([3,1])
with col2:
    tara_btn = st.button("🚀 Tara", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ─── İSTATİSTİKLER ────────────────────────────────────────────────────────────
df = st.session_state.df_firmalar
toplam     = len(df) if df is not None else 0
eposta_say = int(df["E-posta"].astype(bool).sum()) if df is not None and "E-posta" in df.columns else 0
tel_say    = int(df["Telefon"].astype(bool).sum()) if df is not None and "Telefon" in df.columns else 0
durum      = "✅ Bitti" if st.session_state.tarama_bitti else "⏳ Bekliyor"

c1, c2, c3, c4 = st.columns(4)
for col, num, lbl in zip([c1,c2,c3,c4],
                          [toplam, eposta_say, tel_say, durum],
                          ["Toplam Firma","E-posta Bulunan","Telefon Bulunan","Durum"]):
    with col:
        st.markdown(f"""<div class="stat-box">
            <div class="stat-number" style="font-size:{'1.2rem' if isinstance(num,str) else '2rem'}">{num}</div>
            <div class="stat-label">{lbl}</div></div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── TARAMA BAŞLAT ────────────────────────────────────────────────────────────
if tara_btn:
    url_listesi = [u.strip() for u in url_girisi.strip().splitlines() if u.strip()]
    if not url_listesi:
        st.warning("⚠️ En az bir URL girin!")
    else:
        st.session_state.df_firmalar = None
        st.session_state.loglar      = []
        st.session_state.tarama_bitti = False

        durum_kutusu = st.empty()
        log_kutusu   = st.empty()
        progress     = st.progress(0)
        
        tum_df_listesi = []
        
        for i, url in enumerate(url_listesi):
            durum_kutusu.info(f"🌐 Taranıyor ({i+1}/{len(url_listesi)}): {url}")
            
            try:
                df_tek, loglar = osb_universal_tara(url, max_sayfa=max_sayfa, gecikme=gecikme)
                tum_df_listesi.append(df_tek)
                st.session_state.loglar.extend(loglar)
            except Exception as e:
                st.session_state.loglar.append(f"❌ {url}: {e}")
            
            progress.progress((i+1) / len(url_listesi))
            log_icerik = "\n".join(st.session_state.loglar[-12:])
            log_kutusu.markdown(f"<div class=\'log-box\'>{log_icerik}</div>", unsafe_allow_html=True)

        if tum_df_listesi:
            st.session_state.df_firmalar = pd.concat(tum_df_listesi, ignore_index=True)
            st.session_state.tarama_bitti = True
            n = len(st.session_state.df_firmalar)
            durum_kutusu.success(f"🎉 Tarama tamamlandı! **{n} firma** toplandı.")
        else:
            durum_kutusu.error("❌ Hiçbir siteden veri çekilemedi.")
        
        st.rerun()

# ─── LOG GÖSTERİMİ ────────────────────────────────────────────────────────────
if st.session_state.loglar:
    with st.expander("📋 Tarama Logları", expanded=False):
        log_metni = "\n".join(st.session_state.loglar)
        st.code(log_metni, language=None)

# ─── SONUÇ TABLOSU ────────────────────────────────────────────────────────────
if st.session_state.df_firmalar is not None and len(st.session_state.df_firmalar) > 0:
    df = st.session_state.df_firmalar.copy()
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📊 Firma Listesi")
    
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        arama = st.text_input("🔍 Ara...", placeholder="Firma adı veya keyword")
    with col2:
        sutunlar = list(df.columns)
        sektor_sutun = next((s for s in sutunlar if "sekt" in s.lower()), None)
        if sektor_sutun:
            sektorler = ["Tümü"] + sorted(df[sektor_sutun].dropna().unique().tolist())
            secili = st.selectbox("Sektör", sektorler)
        else:
            secili = "Tümü"
    with col3:
        sadece_eposta = st.checkbox("Sadece e-postalılar")

    if arama:
        mask = df.apply(lambda r: arama.lower() in str(r.values).lower(), axis=1)
        df = df[mask]
    if secili != "Tümü" and sektor_sutun:
        df = df[df[sektor_sutun] == secili]
    if sadece_eposta and "E-posta" in df.columns:
        df = df[df["E-posta"].astype(bool)]

    st.dataframe(df, use_container_width=True, height=420)
    st.markdown("</div>", unsafe_allow_html=True)

    # ─── İNDİR ────────────────────────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 💾 Dışa Aktar")
    ad = osb_adi or "osb_firmalar"
    c1, c2, c3 = st.columns(3)
    with c1:
        csv = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("📥 CSV İndir", csv, f"{ad}.csv", "text/csv", use_container_width=True)
    with c2:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="Firmalar")
        st.download_button("📥 Excel İndir", buf.getvalue(), f"{ad}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    with c3:
        if st.button("🗑️ Temizle", use_container_width=True):
            st.session_state.df_firmalar = None
            st.session_state.loglar      = []
            st.session_state.tarama_bitti = False
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="text-align:center;padding:3rem;background:white;border-radius:12px;
                box-shadow:0 2px 10px rgba(0,0,0,0.07)">
        <div style="font-size:4rem">🏭</div>
        <h3 style="color:#444;margin-top:1rem">Henüz tarama yapılmadı</h3>
        <p style="color:#888">Yukarıya OSB URL'lerini girin ve <b>Tara</b> butonuna tıklayın</p>
        <p style="color:#aaa;font-size:0.85rem">💡 İpucu: Birden fazla OSB'yi aynı anda tarayabilirsiniz</p>
    </div>""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;color:#aaa;font-size:0.8rem;padding:1.5rem 1rem 0.5rem">
    OSB Evrensel Firma Tarayıcı • Gumloop AI Agent
</div>""", unsafe_allow_html=True)
