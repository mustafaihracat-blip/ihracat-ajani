import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import io
from urllib.parse import urlparse, urljoin

# ─── SAYFA AYARLARI ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OSB Firma Tarayıcı",
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
    .info-box {
        background: #e8f4fd; border-left: 4px solid #2e86de;
        border-radius: 8px; padding: 1rem 1.2rem; margin-bottom: 1rem;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# ─── SABİTLER ─────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

HABER_KALIPLARI = [
    r"\d{1,2}\s+(ocak|subat|mart|nisan|mayis|haziran|temmuz|agustos|eylul|ekim|kasim|aralik)",
    r"\b(haber|duyuru|etkinlik|toplanti|ziyaret|inceleme|imza|fuar|sergi|galeri)\b",
    r"^(ana sayfa|hakkimizda|iletisim|kurumsal|vizyon|misyon)$",
]

def haber_mi(metin):
    m = metin.lower()
    for k in HABER_KALIPLARI:
        if re.search(k, m):
            return True
    return len(metin) < 3 or len(metin) > 120

def temizle(t):
    return re.sub(r"\s+", " ", str(t)).strip()

def email_bul(html):
    # mailto: linkleri önce kontrol et
    soup = BeautifulSoup(str(html), "html.parser") if not isinstance(html, BeautifulSoup) else html
    for a in soup.select("a[href^=mailto]"):
        ep = a["href"].replace("mailto:", "").split("?")[0].strip()
        if "@" in ep:
            return ep
    # Düz metin içinde ara
    m = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]{2,}", str(html))
    return m[0] if m else ""

def tel_bul(metin):
    m = re.findall(r"[\+\(]?[\d][\d\s\-\.\(\)]{7,}[\d]", str(metin))
    return m[0].strip() if m else ""

def web_bul(html):
    soup = BeautifulSoup(str(html), "html.parser") if not isinstance(html, BeautifulSoup) else html
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if href.startswith("http") and "osb" not in href.lower():
            return href
    return ""

def sayfa_getir(url, timeout=12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.encoding = r.apparent_encoding
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser"), None
    except Exception as e:
        return None, str(e)

# ─── DETAY SAYFASINDAN İLETİŞİM ÇEK ──────────────────────────────────────────
ILETISIM_BOLUM_SEL = [
    ".iletisim", ".contact", ".firma-detay", ".company-detail",
    ".detail", ".info", "#iletisim", "#contact",
    "[class*=iletisim]", "[class*=contact]", "[class*=detail]",
    "table", ".card", "main", "article"
]

def detay_sayfasindan_cek(url):
    """Firma detay sayfasından iletişim bilgilerini toplar"""
    soup, hata = sayfa_getir(url)
    if not soup:
        return {}

    # Tüm sayfada e-posta ara
    eposta = email_bul(soup)

    # İletişim bölümünü bulmaya çalış
    telefon = adres = web = ""
    for sel in ILETISIM_BOLUM_SEL:
        blok = soup.select_one(sel)
        if blok:
            metin = blok.get_text(" ", strip=True)
            if not telefon:
                telefon = tel_bul(metin)
            if not adres:
                # "OSB" veya "Cad" veya "Sk" içeren uzun metin = adres
                adres_m = re.search(r"[A-ZÇĞİÖŞÜa-zçğışöüİ\s]+(?:OSB|Cad|Sk|Blok|No|Mah|Bul)[^<\n]{5,80}", metin)
                if adres_m:
                    adres = adres_m.group().strip()
            if not web:
                web = web_bul(blok)
            if eposta and telefon:
                break

    return {
        "E-posta":    eposta,
        "Telefon":    telefon,
        "Adres":      adres,
        "Web Sitesi": web,
    }

# ─── ANA LİSTE TARAMA ─────────────────────────────────────────────────────────
def liste_tara(url):
    """Firma listesini çeker: isimler + varsa detay URL'leri"""
    soup, hata = sayfa_getir(url)
    if not soup:
        return [], [], hata

    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    firmalar = []
    detay_urller = []

    # ── Tablo yapısı ──
    for tablo in soup.select("table"):
        satirlar = tablo.select("tr")
        if len(satirlar) < 3:
            continue
        baslik_row = satirlar[0].select("th") or satirlar[0].select("td")
        basliklar  = [temizle(b.get_text()) for b in baslik_row]

        for satir in satirlar[1:]:
            hucreler = satir.select("td")
            if not hucreler:
                continue
            ad_hucre = hucreler[0]
            ad = temizle(ad_hucre.get_text())
            if not ad or haber_mi(ad):
                continue

            # Detay linki var mı?
            a_tag = ad_hucre.select_one("a[href]")
            detay_url = urljoin(base, a_tag["href"]) if a_tag else ""

            firma = {"Firma Adı": ad, "Detay URL": detay_url}
            if basliklar:
                for i, bsl in enumerate(basliklar[1:], 1):
                    if i < len(hucreler):
                        firma[bsl if bsl else f"Alan{i}"] = temizle(hucreler[i].get_text())
            # Satır içinde e-posta/tel var mı?
            satir_html = str(satir)
            firma["E-posta"] = email_bul(satir_html)
            firma["Telefon"] = tel_bul(satir.get_text())
            firmalar.append(firma)
            if detay_url:
                detay_urller.append(detay_url)

        if firmalar:
            break

    # ── Kart/Liste yapısı ──
    if not firmalar:
        for sel in ["[class*=firma]", "[class*=company]", "[class*=member]",
                    "[class*=uye]", "li.item", ".liste-row", "li"]:
            kartlar = soup.select(sel)
            if len(kartlar) < 3:
                continue
            for k in kartlar:
                ad_el = k.select_one("h1,h2,h3,h4,h5,strong,.title,.name")
                ad    = temizle(ad_el.get_text()) if ad_el else temizle(k.get_text())[:80]
                if not ad or haber_mi(ad):
                    continue
                a_tag = k.select_one("a[href]")
                detay_url = urljoin(base, a_tag["href"]) if a_tag and a_tag.get("href") else ""
                firmalar.append({
                    "Firma Adı": ad,
                    "Detay URL": detay_url,
                    "E-posta":   email_bul(str(k)),
                    "Telefon":   tel_bul(k.get_text()),
                })
                if detay_url:
                    detay_urller.append(detay_url)
            if firmalar:
                break

    # Sayfalama
    sonraki_sayfalar = []
    for a in soup.select("a[href]"):
        href  = a.get("href", "")
        metin = a.get_text(strip=True).lower()
        if re.search(r"page[=/]\d+|sayfa[=/]\d+|\bsonraki\b|\bnext\b|»", metin + href, re.I):
            sonraki_sayfalar.append(urljoin(base, href))

    return firmalar, sonraki_sayfalar[:8], None

# ─── SESSION STATE ────────────────────────────────────────────────────────────
for k, v in [("df_firmalar", None), ("loglar", []), ("tarama_bitti", False), ("detay_bitti", False)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ─── HERO ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-box">
    <h1>🏭 OSB Firma Tarayıcı</h1>
    <p>Firma listesini çeker &nbsp;•&nbsp; Detay sayfalarından iletişim bilgisi toplar &nbsp;•&nbsp; Excel/CSV aktarır</p>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Ayarlar")
    st.markdown("---")
    max_sayfa    = st.slider("Liste Sayfası (max)", 1, 30, 5)
    gecikme      = st.select_slider("İstek Gecikmesi (sn)", [0.2, 0.5, 1.0, 2.0], value=0.5)
    detay_tara   = st.toggle("🔍 Detay Sayfalarını Tara", value=True,
                              help="Her firmanın OSB detay sayfasına giderek e-posta/telefon çeker")
    max_detay    = st.slider("Maksimum Detay Sayfa", 10, 500, 100, step=10,
                              disabled=not detay_tara)
    st.markdown("---")
    st.markdown("""
### 📌 Nasıl Çalışır?
1. Firma listesi çekilir
2. ✅ **Detay Tara** açıksa her firmanın OSB sayfasına gidilir
3. E-posta, telefon, adres alınır
4. Excel/CSV olarak indirilir
    """)

# ─── URL GİRİŞİ ──────────────────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### 🔗 OSB Firma Listesi URL'si")
st.markdown("""
<div class="info-box">
💡 <b>Doğrudan firma listesi sayfasını gir</b> — örn: <code>https://www.iaosb.org.tr/uyefirmalar</code><br>
Ana sayfayı girersen e-posta bulunamayabilir!
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([4, 1])
with col1:
    hedef_url = st.text_input("", placeholder="https://www.iaosb.org.tr/uyefirmalar",
                               label_visibility="collapsed")
with col2:
    tara_btn = st.button("🚀 Tara", use_container_width=True)

osb_adi = st.text_input("Kayıt adı (dosya için)", placeholder="izmir_ataturk_osb")
st.markdown("</div>", unsafe_allow_html=True)

# ─── İSTATİSTİKLER ────────────────────────────────────────────────────────────
df_s       = st.session_state.df_firmalar
toplam     = len(df_s) if df_s is not None else 0
eposta_say = int(df_s["E-posta"].astype(bool).sum()) if df_s is not None and "E-posta" in df_s.columns else 0
tel_say    = int(df_s["Telefon"].astype(bool).sum())  if df_s is not None and "Telefon" in df_s.columns else 0
durum_txt  = "✅ Bitti" if st.session_state.tarama_bitti else "⏳ Bekliyor"

c1, c2, c3, c4 = st.columns(4)
for col, num, lbl in zip([c1,c2,c3,c4],
                          [toplam, eposta_say, tel_say, durum_txt],
                          ["Toplam Firma","E-posta Bulunan","Telefon Bulunan","Durum"]):
    with col:
        boyut = "1.2rem" if isinstance(num, str) else "2rem"
        st.markdown(f"""<div class="stat-box">
            <div class="stat-number" style="font-size:{boyut}">{num}</div>
            <div class="stat-label">{lbl}</div></div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── TARAMA BAŞLAT ────────────────────────────────────────────────────────────
if tara_btn:
    if not hedef_url.strip():
        st.warning("⚠️ URL girin!")
    else:
        st.session_state.df_firmalar  = None
        st.session_state.loglar       = []
        st.session_state.tarama_bitti = False

        durum_el   = st.empty()
        prog_el    = st.progress(0)
        log_el     = st.empty()

        # ── AŞAMA 1: Firma listesini çek ──────────────────────────────────────
        durum_el.info("📋 Firma listesi çekiliyor...")
        tum_firmalar   = []
        kuyruk         = [hedef_url.strip()]
        ziyaret        = set()
        sayfa_no       = 0
        loglar         = []

        while kuyruk and sayfa_no < max_sayfa:
            url = kuyruk.pop(0)
            if url in ziyaret:
                continue
            ziyaret.add(url)
            sayfa_no += 1

            firmalar, sonraki, hata = liste_tara(url)
            if hata:
                loglar.append(f"❌ Sayfa {sayfa_no}: {hata}")
            else:
                loglar.append(f"✅ Sayfa {sayfa_no}: {len(firmalar)} firma")
                tum_firmalar.extend(firmalar)
                for s in sonraki:
                    if s not in ziyaret:
                        kuyruk.append(s)

            log_el.code("\n".join(loglar[-8:]))
            prog_el.progress(min(30, sayfa_no * 6))
            time.sleep(gecikme)

        loglar.append(f"📊 Toplam {len(tum_firmalar)} firma toplandı")
        durum_el.info(f"📋 {len(tum_firmalar)} firma bulundu. {'Detay sayfaları taranıyor...' if detay_tara else ''}")

        # ── AŞAMA 2: Detay sayfalarından iletişim bilgisi ─────────────────────
        if detay_tara and tum_firmalar:
            detay_sayisi  = 0
            eposta_sayisi = 0
            sinir = min(max_detay, len(tum_firmalar))

            for i, firma in enumerate(tum_firmalar[:sinir]):
                detay_url = firma.get("Detay URL", "").strip()

                # Zaten e-posta varsa detaya gitme
                if firma.get("E-posta"):
                    eposta_sayisi += 1
                    continue

                if not detay_url:
                    continue

                iletisim = detay_sayfasindan_cek(detay_url)
                if iletisim.get("E-posta"):
                    eposta_sayisi += 1
                firma.update({k: v for k, v in iletisim.items() if v and not firma.get(k)})
                detay_sayisi += 1

                pct = 30 + int((i / sinir) * 65)
                prog_el.progress(min(95, pct))
                if i % 5 == 0:
                    loglar.append(f"🔍 Detay {i+1}/{sinir} — e-posta bulunan: {eposta_sayisi}")
                    log_el.code("\n".join(loglar[-8:]))
                time.sleep(gecikme)

            loglar.append(f"✅ Detay tarama bitti — {eposta_sayisi} e-posta bulundu")

        # ── Sonucu kaydet ─────────────────────────────────────────────────────
        df_son = pd.DataFrame(tum_firmalar)
        # Detay URL sütununu gizle (iç kullanım)
        goster_sutunlar = [c for c in df_son.columns if c != "Detay URL"]
        st.session_state.df_firmalar  = df_son[goster_sutunlar]
        st.session_state.loglar       = loglar
        st.session_state.tarama_bitti = True
        prog_el.progress(100)
        durum_el.success(f"🎉 Tamamlandı! {len(tum_firmalar)} firma, {eposta_sayisi if detay_tara else '?'} e-posta")
        st.rerun()

# ─── LOG ──────────────────────────────────────────────────────────────────────
if st.session_state.loglar:
    with st.expander("📋 Tarama Logları"):
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
        sadece_ep = st.checkbox("Sadece e-postalılar")

    if arama:
        mask = df.apply(lambda r: arama.lower() in str(r.values).lower(), axis=1)
        df = df[mask]
    if secili != "Tümü" and sektor_sutun:
        df = df[df[sektor_sutun] == secili]
    if sadece_ep and "E-posta" in df.columns:
        df = df[df["E-posta"].astype(bool)]

    st.dataframe(df, use_container_width=True, height=430)
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
            st.session_state.df_firmalar  = None
            st.session_state.loglar       = []
            st.session_state.tarama_bitti = False
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

else:
    if st.session_state.tarama_bitti:
        st.error("❌ Veri çekilemedi. Logları kontrol et.")
    else:
        st.markdown("""
        <div style="text-align:center;padding:3rem;background:white;border-radius:12px;
                    box-shadow:0 2px 10px rgba(0,0,0,0.07)">
            <div style="font-size:4rem">🏭</div>
            <h3 style="color:#444;margin-top:1rem">Hazır</h3>
            <p style="color:#888">Firma listesi sayfasının URL'sini gir ve <b>Tara</b>'ya bas</p>
            <p style="color:#aaa;font-size:0.85rem">💡 Detay Sayfalarını Tara açık olursa e-posta/telefon da gelir</p>
        </div>""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;color:#aaa;font-size:0.8rem;padding:1.5rem 1rem 0.5rem">
    OSB Firma Tarayıcı • Gumloop AI Agent
</div>""", unsafe_allow_html=True)
