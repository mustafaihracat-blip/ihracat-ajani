import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import io
from urllib.parse import urlparse, urljoin

st.set_page_config(page_title="OSB Firma Tarayıcı", page_icon="🏭", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; }
    .hero-box {
        background: linear-gradient(135deg, #1e3a5f, #2e86de);
        border-radius: 16px; padding: 2rem 2.5rem; color: white;
        margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    .hero-box h1 { font-size: 2rem; margin: 0; }
    .hero-box p  { font-size: 1rem; margin: 0.5rem 0 0; opacity: 0.85; }
    .card { background: white; border-radius: 12px; padding: 1.5rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.07); margin-bottom: 1.2rem; }
    .stat-box { background: white; border-radius: 12px; padding: 1.2rem 1rem;
                text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.07); }
    .stat-number { font-size: 2rem; font-weight: 700; color: #2e86de; }
    .stat-label  { font-size: 0.82rem; color: #666; margin-top: 4px; }
    .stButton > button {
        background: linear-gradient(135deg, #2e86de, #1e3a5f); color: white;
        border: none; border-radius: 8px; padding: 0.6rem 1.5rem;
        font-weight: 600; width: 100%;
    }
    .stButton > button:hover { opacity: 0.88; color: white; }
</style>
""", unsafe_allow_html=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ─── YARDIMCI ─────────────────────────────────────────────────────────────────
def temizle(t):
    return re.sub(r"\s+", " ", str(t)).strip()

def sayfa_getir(url, timeout=12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.encoding = r.apparent_encoding
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser"), None
    except Exception as e:
        return None, str(e)

def email_bul_akilli(soup, kara_liste_domainler):
    """Site emaillerini ve genel domainleri filtreler, firma emailini bulur"""
    # Önce mailto linklerinden
    for a in soup.select("a[href^=mailto]"):
        ep = a["href"].replace("mailto:", "").split("?")[0].strip().lower()
        if "@" not in ep:
            continue
        domain = ep.split("@")[1] if "@" in ep else ""
        # Kara listedeki domainleri atla
        if any(kara in domain for kara in kara_liste_domainler):
            continue
        return ep
    # Düz metinde ara ama kara listeden değilse
    tum_metin = soup.get_text()
    for ep in re.findall(r"[\w.+-]+@[\w-]+\.[\w.]{2,}", tum_metin):
        ep = ep.lower()
        domain = ep.split("@")[1] if "@" in ep else ""
        if any(kara in domain for kara in kara_liste_domainler):
            continue
        return ep
    return ""

def tel_bul_akilli(soup, kara_liste_teller):
    """Site geneli telefon numaralarını filtreler"""
    metin = soup.get_text()
    for tel in re.findall(r"[\+\(]?[\d][\d\s\-\.\(\)]{7,}[\d]", metin):
        tel_temiz = re.sub(r"\D", "", tel)
        if any(kara in tel_temiz for kara in kara_liste_teller):
            continue
        if len(tel_temiz) >= 10:
            return tel.strip()
    return ""

def web_sitesi_bul(soup, ana_domain):
    """Firma web sitesini bulur (OSB domainini hariç tutar)"""
    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        if not href.startswith("http"):
            continue
        if ana_domain in href:
            continue
        # Geçerli domain gibi görünüyor mu?
        if re.match(r"https?://[\w.-]+\.[a-z]{2,}", href):
            return href
    return ""

# ─── SITE ANALİZİ: İLK SAYFADAN KARA LİSTEYİ OTOMATİK ÇIKAR ────────────────
def site_karaliste_cikar(ana_url):
    """Ana sayfadan sitenin kendi email ve telefon numaralarını tespit eder"""
    soup, _ = sayfa_getir(ana_url)
    kara_emailler = []
    kara_teller   = []
    ana_domain    = urlparse(ana_url).netloc.replace("www.", "")

    if soup:
        # Sitenin kendi emaillerini bul
        for a in soup.select("a[href^=mailto]"):
            ep = a["href"].replace("mailto:", "").split("?")[0].strip().lower()
            if "@" in ep:
                domain = ep.split("@")[1]
                kara_emailler.append(domain)

        # Sitenin kendi telefon numaralarını bul (ilk 3 hane yeterli)
        footer = soup.select_one("footer, .footer, #footer, .iletisim, #iletisim")
        if footer:
            for tel in re.findall(r"[\+\(]?[\d][\d\s\-\.\(\)]{7,}[\d]", footer.get_text()):
                tel_temiz = re.sub(r"\D", "", tel)[:7]  # İlk 7 rakam
                if tel_temiz:
                    kara_teller.append(tel_temiz)

    kara_emailler.append(ana_domain)  # Her zaman ana domaini kara listeye ekle
    return list(set(kara_emailler)), list(set(kara_teller))

# ─── FİRMA LİSTESİNİ ÇEK ─────────────────────────────────────────────────────
def firma_listesi_cek(url, ana_domain):
    """Sayafadan firma adı + detay URL'si çeker"""
    soup, hata = sayfa_getir(url)
    if not soup:
        return [], [], hata

    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    firmalar = []

    # ── Tablo yapısı ──
    for tablo in soup.select("table"):
        satirlar = tablo.select("tr")
        if len(satirlar) < 3:
            continue
        for satir in satirlar[1:]:
            hucreler = satir.select("td")
            if not hucreler:
                continue
            ad = temizle(hucreler[0].get_text())
            if not ad or len(ad) < 3:
                continue
            # Haber/tarih filtresi
            if re.search(r"\d{1,2}\s+(ocak|şubat|mart|nisan|mayıs|haziran|"
                         r"temmuz|ağustos|eylül|ekim|kasım|aralık)", ad, re.I):
                continue
            # Detay linki
            a_tag = hucreler[0].select_one("a[href]")
            detay = urljoin(base, a_tag["href"]) if a_tag else ""
            # /iletisim-bilgileri ve benzeri sayfaları atla
            if "iletisim-bilgileri" in detay or "iletisim_bilgileri" in detay:
                continue
            firmalar.append({
                "Firma Adı":  ad,
                "_detay_url": detay,
                "Sektör":     temizle(hucreler[1].get_text()) if len(hucreler) > 1 else "",
                "E-posta":    "",
                "Telefon":    "",
                "Web Sitesi": "",
                "Adres":      "",
            })
        if firmalar:
            break

    # ── Kart/liste yapısı ──
    if not firmalar:
        for sel in ["[class*=firma]", "[class*=company]", "[class*=member]",
                    "[class*=uye]", "article", ".item", "li"]:
            kartlar = soup.select(sel)
            if len(kartlar) < 3:
                continue
            for k in kartlar:
                ad_el = k.select_one("h1,h2,h3,h4,strong,.title,.name")
                ad    = temizle(ad_el.get_text()) if ad_el else temizle(k.get_text())[:80]
                if not ad or len(ad) < 3:
                    continue
                if re.search(r"\d{4}", ad):
                    continue
                a_tag = k.select_one("a[href]")
                detay = urljoin(base, a_tag["href"]) if a_tag and a_tag.get("href") else ""
                if "iletisim" in detay:
                    continue
                firmalar.append({
                    "Firma Adı":  ad,
                    "_detay_url": detay,
                    "E-posta":    "",
                    "Telefon":    "",
                    "Web Sitesi": "",
                })
            if firmalar:
                break

    # Sonraki sayfalar
    sonraki = []
    for a in soup.select("a[href]"):
        href  = a.get("href", "")
        metin = a.get_text(strip=True).lower()
        if re.search(r"page[=/]\d+|sayfa[=/]\d+|\bsonraki\b|\bnext\b|»", metin + href, re.I):
            tam = urljoin(base, href)
            if tam != url:
                sonraki.append(tam)

    return firmalar, list(set(sonraki))[:8], None

# ─── DETAY SAYFASINDAN İLETİŞİM ÇEK ──────────────────────────────────────────
def detay_iletisim_cek(url, kara_emailler, kara_teller, ana_domain):
    soup, hata = sayfa_getir(url)
    if not soup:
        return {}

    eposta  = email_bul_akilli(soup, kara_emailler)
    telefon = tel_bul_akilli(soup, kara_teller)
    web     = web_sitesi_bul(soup, ana_domain)

    # Adres için OSB/Cad/Mah içeren metin
    adres = ""
    for tag in soup.select("p, td, .adres, .address, [class*=adres], [class*=address]"):
        t = temizle(tag.get_text())
        if re.search(r"(osb|cad\.|sok\.|mah\.|blok|no:|organize sanayi)", t, re.I):
            if 15 < len(t) < 200:
                adres = t
                break

    return {
        "E-posta":    eposta,
        "Telefon":    telefon,
        "Web Sitesi": web,
        "Adres":      adres,
    }

# ─── ANA TARAMA ───────────────────────────────────────────────────────────────
def tum_osb_tara(liste_url, max_liste_sayfa, max_detay, gecikme, detay_mod):
    loglar       = []
    ana_domain   = urlparse(liste_url).netloc.replace("www.", "")

    # Kara listeyi çıkar
    loglar.append("🔍 Site analizi yapılıyor (kara liste)...")
    kara_emailler, kara_teller = site_karaliste_cikar(liste_url)
    loglar.append(f"🚫 Kara liste email: {kara_emailler}")
    loglar.append(f"🚫 Kara liste tel: {kara_teller}")

    # Firma listesini çek
    tum_firmalar = []
    kuyruk       = [liste_url]
    ziyaret      = set()
    sayfa_no     = 0

    while kuyruk and sayfa_no < max_liste_sayfa:
        url = kuyruk.pop(0)
        if url in ziyaret:
            continue
        ziyaret.add(url)
        sayfa_no += 1
        firmalar, sonraki, hata = firma_listesi_cek(url, ana_domain)
        if hata:
            loglar.append(f"❌ Sayfa {sayfa_no}: {hata}")
        else:
            loglar.append(f"✅ Sayfa {sayfa_no}: {len(firmalar)} firma")
            tum_firmalar.extend(firmalar)
            for s in sonraki:
                if s not in ziyaret:
                    kuyruk.append(s)
        time.sleep(gecikme)

    # Tekrarları kaldır
    goruldu = set()
    benzersiz = []
    for f in tum_firmalar:
        if f["Firma Adı"] not in goruldu:
            goruldu.add(f["Firma Adı"])
            benzersiz.append(f)
    tum_firmalar = benzersiz

    loglar.append(f"📊 Toplam {len(tum_firmalar)} benzersiz firma")

    # Detay sayfalarını tara
    eposta_bulunan = 0
    if detay_mod:
        sinir = min(max_detay, len(tum_firmalar))
        loglar.append(f"🔍 {sinir} firmada detay taraması başlıyor...")

        for i, firma in enumerate(tum_firmalar[:sinir]):
            detay_url = firma.get("_detay_url", "").strip()
            if not detay_url or "iletisim-bilgileri" in detay_url:
                continue

            iletisim = detay_iletisim_cek(detay_url, kara_emailler, kara_teller, ana_domain)
            for k, v in iletisim.items():
                if v:
                    firma[k] = v
            if firma.get("E-posta"):
                eposta_bulunan += 1

            if (i + 1) % 10 == 0:
                loglar.append(f"  ↳ {i+1}/{sinir} detay tarandı — {eposta_bulunan} e-posta")
            time.sleep(gecikme)

        loglar.append(f"✅ Detay tamamlandı: {eposta_bulunan} e-posta bulundu")

    # _detay_url sütununu kaldır
    for f in tum_firmalar:
        f.pop("_detay_url", None)

    return pd.DataFrame(tum_firmalar), loglar

# ─── SESSION STATE ────────────────────────────────────────────────────────────
for k, v in [("df", None), ("loglar", []), ("bitti", False)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ─── HERO ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-box">
    <h1>🏭 OSB Firma Tarayıcı</h1>
    <p>Firma listesini çeker &nbsp;•&nbsp; Detay sayfalarından iletişim bilgisi toplar &nbsp;•&nbsp;
    Site emaillerini otomatik filtreler</p>
</div>""", unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Ayarlar")
    st.markdown("---")
    max_liste  = st.slider("Firma Listesi Sayfası", 1, 30, 5)
    gecikme    = st.select_slider("Gecikme (sn)", [0.2, 0.5, 1.0, 1.5], value=0.5)
    detay_mod  = st.toggle("🔍 Detay Sayfaları Tara", value=True)
    max_detay  = st.slider("Max Detay Sayfa", 10, 1000, 200, 10, disabled=not detay_mod)
    st.markdown("---")
    st.info("🚫 Sitenin kendi e-postası otomatik filtrelenir\n\n"
            "✅ Sadece firmaya ait iletişim bilgileri gösterilir")

# ─── URL GİRİŞİ ──────────────────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### 🔗 Firma Listesi URL'si")
c1, c2 = st.columns([4, 1])
with c1:
    url_input = st.text_input("", placeholder="https://www.iaosb.org.tr/uyefirmalar",
                               label_visibility="collapsed")
with c2:
    tara_btn = st.button("🚀 Tara", use_container_width=True)
osb_adi = st.text_input("Kayıt adı", placeholder="izmir_ataturk_osb")
st.markdown("</div>", unsafe_allow_html=True)

# ─── İSTATİSTİKLER ────────────────────────────────────────────────────────────
df_s  = st.session_state.df
top   = len(df_s) if df_s is not None else 0
ep    = int(df_s["E-posta"].astype(bool).sum())   if df_s is not None and "E-posta"  in df_s.columns else 0
tel   = int(df_s["Telefon"].astype(bool).sum())   if df_s is not None and "Telefon"  in df_s.columns else 0
web   = int(df_s["Web Sitesi"].astype(bool).sum())if df_s is not None and "Web Sitesi" in df_s.columns else 0

c1, c2, c3, c4 = st.columns(4)
for col, num, lbl in zip([c1,c2,c3,c4], [top, ep, tel, web],
                          ["Toplam Firma","E-posta","Telefon","Web Sitesi"]):
    with col:
        st.markdown(f"""<div class="stat-box">
            <div class="stat-number">{num}</div>
            <div class="stat-label">{lbl}</div></div>""", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ─── TARAMA ───────────────────────────────────────────────────────────────────
if tara_btn:
    if not url_input.strip():
        st.warning("URL girin!")
    else:
        st.session_state.df    = None
        st.session_state.loglar = []
        st.session_state.bitti = False

        prog  = st.progress(0)
        durum = st.empty()
        log_el= st.empty()

        durum.info("🚀 Tarama başlatılıyor...")

        def progress_cb(pct, mesaj):
            prog.progress(min(pct, 99))
            durum.info(mesaj)

        # Aşama göstergesi
        prog.progress(5)
        durum.info("📋 Firma listesi çekiliyor...")

        df_sonuc, loglar = tum_osb_tara(
            url_input.strip(), max_liste, max_detay, gecikme, detay_mod
        )

        log_el.code("\n".join(loglar[-15:]))
        st.session_state.loglar = loglar
        prog.progress(100)

        if df_sonuc is not None and len(df_sonuc) > 0:
            st.session_state.df    = df_sonuc
            st.session_state.bitti = True
            ep_say = int(df_sonuc["E-posta"].astype(bool).sum()) if "E-posta" in df_sonuc.columns else 0
            durum.success(f"🎉 Tamamlandı! {len(df_sonuc)} firma, {ep_say} e-posta bulundu.")
        else:
            durum.error("❌ Veri çekilemedi. Logları kontrol et.")
        st.rerun()

# ─── LOG ──────────────────────────────────────────────────────────────────────
if st.session_state.loglar:
    with st.expander("📋 Tarama Logları"):
        st.code("\n".join(st.session_state.loglar), language=None)

# ─── SONUÇ TABLOSU ────────────────────────────────────────────────────────────
if st.session_state.df is not None and len(st.session_state.df) > 0:
    df = st.session_state.df.copy()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📊 Firma Listesi")

    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        ara = st.text_input("🔍 Ara...", placeholder="Firma adı")
    with c2:
        sek_col = next((s for s in df.columns if "sekt" in s.lower()), None)
        if sek_col:
            sek_list = ["Tümü"] + sorted(df[sek_col].dropna().unique().tolist())
            sek_sec  = st.selectbox("Sektör", sek_list)
        else:
            sek_sec = "Tümü"
    with c3:
        sadece_ep = st.checkbox("Sadece e-postalılar")

    if ara:
        df = df[df.apply(lambda r: ara.lower() in str(r.values).lower(), axis=1)]
    if sek_sec != "Tümü" and sek_col:
        df = df[df[sek_col] == sek_sec]
    if sadece_ep and "E-posta" in df.columns:
        df = df[df["E-posta"].astype(bool)]

    st.dataframe(df, use_container_width=True, height=430)
    st.markdown("</div>", unsafe_allow_html=True)

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
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)
    with c3:
        if st.button("🗑️ Temizle", use_container_width=True):
            st.session_state.df = None
            st.session_state.loglar = []
            st.session_state.bitti = False
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="text-align:center;padding:3rem;background:white;border-radius:12px;
                box-shadow:0 2px 10px rgba(0,0,0,0.07)">
        <div style="font-size:4rem">🏭</div>
        <h3 style="color:#444;margin-top:1rem">Hazır</h3>
        <p style="color:#888">Firma listesi URL'sini gir, <b>Tara</b>'ya bas</p>
        <p style="color:#aaa;font-size:0.85rem">
        💡 Site emaili otomatik filtrelenir — sadece firma iletişim bilgileri gelir</p>
    </div>""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;color:#aaa;font-size:0.8rem;padding:1.5rem 1rem 0.5rem">
    OSB Firma Tarayıcı • Gumloop AI Agent
</div>""", unsafe_allow_html=True)
