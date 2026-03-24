import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import io

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
    eslesmeler = re.findall(r"https?://[^\s\"\'<>]+", str(metin))
    return eslesmeler[0] if eslesmeler else ""

# ─── STRATEJİ 1: TABLO TARAMA ─────────────────────────────────────────────────
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
                firma["Sektör"]    = hucreler[1] if len(hucreler) > 1 else ""
                firma["Telefon"]   = hucreler[2] if len(hucreler) > 2 else ""
                firma["E-posta"]   = hucreler[3] if len(hucreler) > 3 else ""
                firma["Adres"]     = hucreler[4] if len(hucreler) > 4 else ""
            firmalar.append(firma)
    return firmalar

# ─── STRATEJİ 2: KART / LİSTE TARAMA ─────────────────────────────────────────
KART_SELECTORS = [
    ".firma", ".company", ".member", ".uye", ".uye-firma",
    ".card", ".liste-item", ".item", "article", ".post",
    "[class*=firma]", "[class*=company]", "[class*=member]",
    "[class*=uye]", "[class*=card]"
]

def strateji_kart(soup):
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
                "Firma Adı":  temizle(baslik.get_text()) if baslik else tam_metin[:60],
                "E-posta":    email_bul(str(kart)),
                "Telefon":    tel_bul(tam_metin),
                "Web Sitesi": url_bul(str(kart)),
                "Ham Metin":  tam_metin[:200],
            }
            if firma["Firma Adı"]:
                firmalar.append(firma)
        if firmalar:
            return firmalar
    return firmalar

# ─── STRATEJİ 3: REGEX / MAILTO TARAMA ───────────────────────────────────────
def strateji_regex(soup):
    firmalar = []
    for a in soup.select("a[href^=mailto]"):
        eposta  = a["href"].replace("mailto:", "").split("?")[0].strip()
        ebeveyn = a.find_parent(["li", "div", "tr", "td", "section", "article"])
        metin   = temizle(ebeveyn.get_text()) if ebeveyn else temizle(a.get_text())
        firmalar.append({
            "Firma Adı": metin[:80] if metin else eposta,
            "E-posta":   eposta,
            "Telefon":   tel_bul(metin),
            "Ham Metin": metin[:200],
        })
    return firmalar

# ─── SONRAKİ SAYFALARI BUL ────────────────────────────────────────────────────
def sonraki_sayfalar_bul(soup, base_url):
    linkler = set()
    for a in soup.select("a[href]"):
        href  = a.get("href", "")
        metin = temizle(a.get_text()).lower()
        if re.search(r"page[=/\\]\d+|sayfa\d+|\bpage\b|sonraki|ileri|next|>", metin + href, re.I):
            if href.startswith("http"):
                linkler.add(href)
            elif href.startswith("/"):
                from urllib.parse import urlparse
                p = urlparse(base_url)
                linkler.add(f"{p.scheme}://{p.netloc}{href}")
    return list(linkler)[:10]

# ─── ANA TARAMA FONKSİYONU ────────────────────────────────────────────────────
def osb_universal_tara(url, max_sayfa=20, gecikme=0.5):
    tum_firmalar  = []
    loglar        = []
    ziyaret       = set()
    kuyruk        = [url]
    sayfa_no      = 0

    while kuyruk and sayfa_no < max_sayfa:
        mevcut = kuyruk.pop(0)
        if mevcut in ziyaret:
            continue
        ziyaret.add(mevcut)
        sayfa_no += 1

        try:
            resp = requests.get(mevcut, headers=HEADERS, timeout=15)
            resp.encoding = resp.apparent_encoding
            resp.raise_for_status()
        except Exception as e:
            loglar.append(f"❌ Sayfa {sayfa_no}: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        firmalar = strateji_tablo(soup)
        if firmalar:
            loglar.append(f"✅ Sayfa {sayfa_no} — Tablo → {len(firmalar)} firma")
        else:
            firmalar = strateji_kart(soup)
            if firmalar:
                loglar.append(f"✅ Sayfa {sayfa_no} — Kart → {len(firmalar)} firma")
            else:
                firmalar = strateji_regex(soup)
                if firmalar:
                    loglar.append(f"✅ Sayfa {sayfa_no} — Regex → {len(firmalar)} firma")
                else:
                    loglar.append(f"⚠️ Sayfa {sayfa_no} — Veri bulunamadı")

        for f in firmalar:
            f["Kaynak"] = mevcut
        tum_firmalar.extend(firmalar)

        if sayfa_no == 1:
            yeni = sonraki_sayfalar_bul(soup, url)
            for y in yeni:
                if y not in ziyaret:
                    kuyruk.append(y)
            if yeni:
                loglar.append(f"🔗 {len(yeni)} ek sayfa kuyruğa eklendi")

        time.sleep(gecikme)

    df = pd.DataFrame(tum_firmalar).drop_duplicates()
    return df, loglar

# ─── SESSION STATE ────────────────────────────────────────────────────────────
if "df_firmalar"    not in st.session_state: st.session_state.df_firmalar    = None
if "loglar"         not in st.session_state: st.session_state.loglar         = []
if "tarama_bitti"   not in st.session_state: st.session_state.tarama_bitti   = False

# ─── HERO ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-box">
    <h1>🏭 OSB Evrensel Firma Tarayıcı</h1>
    <p>Her OSB sitesini otomatik analiz eder &nbsp;•&nbsp; Tablo / Kart / Regex stratejileri &nbsp;•&nbsp; Sayfalama desteği</p>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Tarama Ayarları")
    st.markdown("---")
    max_sayfa = st.slider("Maksimum Sayfa", 1, 50, 10)
    gecikme   = st.select_slider("İstek Gecikmesi (sn)", [0.2, 0.5, 1.0, 2.0], value=0.5)
    st.markdown("---")
    st.markdown("### 📌 Strateji Sırası")
    st.success("1️⃣ Tablo Tarama")
    st.info("2️⃣ Kart / Liste Tarama")
    st.warning("3️⃣ Regex / E-posta Tarama")
    st.markdown("---")
    st.caption("Sırayla denenir. İlk sonuç veren strateji kullanılır.")

# ─── ÇOKLU URL GİRİŞİ ────────────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### 🔗 OSB Web Sitesi / Siteleri")
st.caption("Birden fazla OSB girebilirsin — her satıra bir URL")
url_girisi = st.text_area(
    label="",
    placeholder="https://www.iosb.org.tr/uyefirmalar\nhttps://www.bosb.org.tr/firmalar\nhttps://www.aosb.org.tr/uyeler",
    height=110,
    label_visibility="collapsed"
)
osb_adi = st.text_input("Kayıt Adı (dosya adı için)", placeholder="istanbul_osb")
col1, col2 = st.columns([3, 1])
with col2:
    tara_btn = st.button("🚀 Tara", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ─── İSTATİSTİKLER ────────────────────────────────────────────────────────────
df_s       = st.session_state.df_firmalar
toplam     = len(df_s) if df_s is not None else 0
eposta_say = int(df_s["E-posta"].astype(bool).sum()) if df_s is not None and "E-posta" in df_s.columns else 0
tel_say    = int(df_s["Telefon"].astype(bool).sum())  if df_s is not None and "Telefon" in df_s.columns else 0
durum_txt  = "✅ Tamamlandı" if st.session_state.tarama_bitti else "⏳ Bekliyor"

c1, c2, c3, c4 = st.columns(4)
for col, num, lbl in zip(
    [c1, c2, c3, c4],
    [toplam, eposta_say, tel_say, durum_txt],
    ["Toplam Firma", "E-posta Bulunan", "Telefon Bulunan", "Durum"]
):
    with col:
        boyut = "1.2rem" if isinstance(num, str) else "2rem"
        st.markdown(f"""<div class="stat-box">
            <div class="stat-number" style="font-size:{boyut}">{num}</div>
            <div class="stat-label">{lbl}</div></div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── TARAMA BAŞLAT ────────────────────────────────────────────────────────────
if tara_btn:
    url_listesi = [u.strip() for u in url_girisi.strip().splitlines() if u.strip()]
    if not url_listesi:
        st.warning("⚠️ En az bir URL girin!")
    else:
        st.session_state.df_firmalar  = None
        st.session_state.loglar       = []
        st.session_state.tarama_bitti = False

        durum_kutusu = st.empty()
        log_kutusu   = st.empty()
        progress     = st.progress(0)
        tum_df       = []

        for i, url in enumerate(url_listesi):
            durum_kutusu.info(f"🌐 Taranıyor ({i+1}/{len(url_listesi)}): {url}")
            try:
                df_tek, loglar = osb_universal_tara(url, max_sayfa=max_sayfa, gecikme=gecikme)
                tum_df.append(df_tek)
                st.session_state.loglar.extend(loglar)
            except Exception as e:
                st.session_state.loglar.append(f"❌ {url}: {e}")
            progress.progress((i + 1) / len(url_listesi))
            log_kutusu.code("\n".join(st.session_state.loglar[-12:]))

        if tum_df:
            st.session_state.df_firmalar  = pd.concat(tum_df, ignore_index=True)
            st.session_state.tarama_bitti = True
            n = len(st.session_state.df_firmalar)
            durum_kutusu.success(f"🎉 Tamamlandı! **{n} firma** toplandı.")
        else:
            durum_kutusu.error("❌ Hiçbir siteden veri çekilemedi.")
        st.rerun()

# ─── LOG GÖSTERİMİ ────────────────────────────────────────────────────────────
if st.session_state.loglar:
    with st.expander("📋 Tarama Logları", expanded=False):
        st.code("\n".join(st.session_state.loglar), language=None)

# ─── SONUÇ TABLOSU ────────────────────────────────────────────────────────────
if st.session_state.df_firmalar is not None and len(st.session_state.df_firmalar) > 0:
    df = st.session_state.df_firmalar.copy()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📊 Firma Listesi")

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        arama = st.text_input("🔍 Ara...", placeholder="Firma adı veya keyword")
    with col2:
        sektor_sutun = next((s for s in df.columns if "sekt" in s.lower()), None)
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
        st.download_button(
            "📥 Excel İndir", buf.getvalue(), f"{ad}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    with c3:
        if st.button("🗑️ Temizle", use_container_width=True):
            st.session_state.df_firmalar  = None
            st.session_state.loglar       = []
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
