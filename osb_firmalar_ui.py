import streamlit as st
import pandas as pd
import openpyxl
import io
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin, quote_plus
import time

st.set_page_config(page_title="OSB Firma Tarayıcı", page_icon="🏭", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; }
    .hero { background: linear-gradient(135deg,#1F4E79,#2e86de);
            border-radius:16px; padding:2rem 2.5rem; color:white; margin-bottom:1.5rem; }
    .hero h1 { font-size:2rem; margin:0; }
    .hero p  { margin:.5rem 0 0; opacity:.85; }
    .card { background:white; border-radius:12px; padding:1.5rem;
            box-shadow:0 2px 10px rgba(0,0,0,.07); margin-bottom:1.2rem; }
    .stat { background:white; border-radius:12px; padding:1.2rem;
            text-align:center; box-shadow:0 2px 10px rgba(0,0,0,.07); }
    .stat-n { font-size:2rem; font-weight:700; color:#1F4E79; }
    .stat-l { font-size:.82rem; color:#666; }
    .adim { background:#f0f4ff; border-left:4px solid #2e86de;
            border-radius:8px; padding:1rem 1.5rem; margin-bottom:1rem; }
    .adim h3 { margin:0 0 .5rem 0; color:#1F4E79; }
    .stButton>button { background:linear-gradient(135deg,#2e86de,#1F4E79);
        color:white; border:none; border-radius:8px; font-weight:600; width:100%; }
</style>
""", unsafe_allow_html=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────

def temizle(t):
    return re.sub(r"\s+", " ", str(t)).strip()

def email_bul(metin):
    kirli = ["noreply","no-reply","example","test@","@sentry","@github","@email"]
    for ep in re.findall(r"[\w.+-]+@[\w-]+\.[\w.]{2,}", str(metin)):
        if not any(k in ep.lower() for k in kirli):
            return ep.lower()
    return ""

def tel_bul(metin):
    m = re.findall(r"(\+90|0)[\s\-\(\)]?\d{3}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}", str(metin))
    return re.sub(r"\s+", " ", m[0]).strip() if m else ""

def sayfa_getir(url, timeout=10):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.encoding = r.apparent_encoding
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser"), None
    except Exception as e:
        return None, str(e)

# ── ADIM 1: OSB sitesinden firma isimlerini çek ───────────────────────────────

def firma_isimlerini_cek(liste_url, max_sayfa=5):
    base = f"{urlparse(liste_url).scheme}://{urlparse(liste_url).netloc}"
    firmalar, kuyruk, ziyaret, loglar = [], [liste_url], set(), []

    while kuyruk and len(ziyaret) < max_sayfa:
        url = kuyruk.pop(0)
        if url in ziyaret:
            continue
        ziyaret.add(url)
        soup, hata = sayfa_getir(url)
        if not soup:
            loglar.append(f"❌ {url}: {hata}")
            continue

        sayfa_f = []

        # Tablo
        for tablo in soup.select("table"):
            satirlar = tablo.select("tr")
            if len(satirlar) < 3:
                continue
            for satir in satirlar[1:]:
                hc = satir.select("td")
                if not hc:
                    continue
                ad = temizle(hc[0].get_text())
                if len(ad) < 3 or re.search(r"\d{4}", ad):
                    continue
                a = hc[0].select_one("a[href]")
                det = urljoin(base, a["href"]) if a else ""
                if "iletisim" in det.lower():
                    continue
                sek = temizle(hc[1].get_text()) if len(hc) > 1 else ""
                sayfa_f.append({"Firma Adı": ad, "_detay": det, "Sektör": sek})
            if sayfa_f:
                break

        # Kart / liste
        if not sayfa_f:
            for sel in ["[class*=firma]","[class*=uye]","[class*=member]","article","li"]:
                kartlar = soup.select(sel)
                if len(kartlar) < 3:
                    continue
                for k in kartlar:
                    ae = k.select_one("h1,h2,h3,h4,strong,.title")
                    ad = temizle(ae.get_text()) if ae else temizle(k.get_text())[:80]
                    if len(ad) < 3 or re.search(r"\d{4}", ad):
                        continue
                    a = k.select_one("a[href]")
                    det = urljoin(base, a["href"]) if a and a.get("href") else ""
                    sayfa_f.append({"Firma Adı": ad, "_detay": det, "Sektör": ""})
                if sayfa_f:
                    break

        firmalar.extend(sayfa_f)
        loglar.append(f"✅ Sayfa {len(ziyaret)}: {len(sayfa_f)} firma")

        # Sonraki sayfa linkleri
        for a in soup.select("a[href]"):
            h = a.get("href", "")
            mt = a.get_text(strip=True).lower()
            if re.search(r"page[=/]\d+|sayfa[=/]\d+|\bsonraki\b|\bnext\b|»", mt + h, re.I):
                t = urljoin(base, h)
                if t not in ziyaret:
                    kuyruk.append(t)
        time.sleep(0.5)

    # Tekrar kaldır
    goruldu, benzersiz = set(), []
    for f in firmalar:
        if f["Firma Adı"] not in goruldu:
            goruldu.add(f["Firma Adı"])
            benzersiz.append(f)
    return benzersiz, loglar

# ── ADIM 2: DuckDuckGo ile iletişim bilgisi bul ──────────────────────────────

def ddg_ara(firma_adi, sehir=""):
    sorgu = f'"{firma_adi}" {sehir} iletişim telefon email'.strip()
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(sorgu)}"
    hdrs = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9",
        "Referer": "https://duckduckgo.com/",
    }
    try:
        r = requests.get(url, headers=hdrs, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        metin = " ".join(s.get_text() for s in soup.select(".result__body,.result__snippet")[:5])
        web = ""
        for a in soup.select(".result__url")[:3]:
            h = a.get_text(strip=True)
            if h and "duckduckgo" not in h:
                web = ("https://" + h) if not h.startswith("http") else h
                break
        return {"E-posta": email_bul(metin), "Telefon": tel_bul(metin), "Web Sitesi": web}
    except:
        return {"E-posta": "", "Telefon": "", "Web Sitesi": ""}

def iletisim_bul(firma_adi, sehir, detay_url):
    ep = tel = web = ""
    osb_domain = urlparse(detay_url).netloc.replace("www.", "") if detay_url else ""

    # 1. OSB detay sayfası
    if detay_url and "iletisim" not in detay_url.lower():
        soup, _ = sayfa_getir(detay_url)
        if soup:
            ep2  = email_bul(str(soup))
            tel2 = tel_bul(soup.get_text())
            if ep2 and osb_domain not in ep2:
                ep = ep2
            if tel2:
                tel = tel2

    # 2. DuckDuckGo (detayda bulunamazsa)
    if not ep and not tel:
        s = ddg_ara(firma_adi, sehir)
        ep  = s.get("E-posta", "")
        tel = s.get("Telefon", "")
        web = s.get("Web Sitesi", "")
        time.sleep(0.8)

    return {"E-posta": ep, "Telefon": tel, "Web Sitesi": web}

# ── Session state ─────────────────────────────────────────────────────────────

for k, v in [("df_isimler", None), ("df_iletisim", None), ("loglar", [])]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Hero ──────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <h1>🏭 OSB Firma Tarayıcı</h1>
  <p>
    Adım 1: OSB sitesinden firma isimlerini çek &nbsp;→&nbsp;
    Adım 2: DuckDuckGo ile iletişim bilgisi bul &nbsp;→&nbsp;
    Adım 3: Excel indir
  </p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Ayarlar")
    st.markdown("---")
    max_sayfa   = st.slider("Liste sayfası (max)", 1, 20, 5)
    sehir_input = st.text_input("Şehir adı (arama kalitesini artırır)",
                                 placeholder="İzmir, Bursa, Gaziantep...")
    gecikme     = st.select_slider("Gecikme (sn)", [0.5, 1.0, 1.5, 2.0], value=1.0)
    st.markdown("---")
    st.success("✅ API key gerekmez!\n\n🔍 DuckDuckGo ile email + telefon")

# ── ADIM 1 ────────────────────────────────────────────────────────────────────

st.markdown('<div class="adim"><h3>📋 Adım 1 — Firma İsimlerini Çek</h3></div>', unsafe_allow_html=True)
st.markdown('<div class="card">', unsafe_allow_html=True)

c1, c2 = st.columns([4, 1])
with c1:
    osb_url = st.text_input("", placeholder="https://www.iaosb.org.tr/uyefirmalar",
                             label_visibility="collapsed")
with c2:
    btn1 = st.button("📋 Çek", use_container_width=True)

if btn1:
    if not osb_url.strip():
        st.warning("URL girin!")
    else:
        with st.spinner("Çekiliyor..."):
            firmalar, loglar = firma_isimlerini_cek(osb_url.strip(), max_sayfa)
        st.session_state.df_isimler = pd.DataFrame(firmalar)
        st.session_state.loglar = loglar
        st.success(f"✅ {len(firmalar)} firma bulundu!")
        st.rerun()

if st.session_state.df_isimler is not None:
    df_i = st.session_state.df_isimler
    st.info(f"✅ {len(df_i)} firma hazır")
    goster = [c for c in ["Firma Adı","Sektör"] if c in df_i.columns]
    st.dataframe(df_i[goster].head(10), use_container_width=True, height=200)
    if len(df_i) > 10:
        st.caption(f"... ve {len(df_i)-10} firma daha")

st.markdown("</div>", unsafe_allow_html=True)

# ── ADIM 2 ────────────────────────────────────────────────────────────────────

if st.session_state.df_isimler is not None and len(st.session_state.df_isimler) > 0:
    st.markdown('<div class="adim"><h3>🔍 Adım 2 — İletişim Bilgisi Bul</h3></div>',
                unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)

    df_i = st.session_state.df_isimler
    c1, c2 = st.columns([3, 1])
    with c1:
        max_ara = st.slider("Kaç firmayı ara?", 5, len(df_i), min(50, len(df_i)), 5)
    with c2:
        btn2 = st.button("🔍 Başlat", use_container_width=True, type="primary")

    if btn2:
        liste    = df_i.to_dict("records")[:max_ara]
        sonuclar = []
        prog     = st.progress(0)
        durum    = st.empty()
        canli    = st.empty()
        ep_say   = 0

        for i, f in enumerate(liste):
            ad  = f.get("Firma Adı", "")
            det = f.get("_detay", "")
            durum.info(f"🔍 [{i+1}/{max_ara}] {ad[:55]}...")
            ile = iletisim_bul(ad, sehir_input, det)

            satir = {
                "Firma Adı":  ad,
                "Sektör":     f.get("Sektör", ""),
                "E-posta":    ile["E-posta"],
                "Telefon":    ile["Telefon"],
                "Web Sitesi": ile["Web Sitesi"],
            }
            sonuclar.append(satir)
            if satir["E-posta"] or satir["Telefon"]:
                ep_say += 1

            st.session_state.df_iletisim = pd.DataFrame(sonuclar)
            prog.progress((i + 1) / max_ara)
            canli.dataframe(pd.DataFrame(sonuclar).tail(5), use_container_width=True)
            time.sleep(gecikme)

        durum.success(f"🎉 Bitti! {max_ara} firma tarandı — {ep_say} iletişim bulundu.")
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ── SONUÇLAR ──────────────────────────────────────────────────────────────────

if st.session_state.df_iletisim is not None and len(st.session_state.df_iletisim) > 0:
    df = st.session_state.df_iletisim.copy()

    ep  = int(df["E-posta"].astype(bool).sum())
    tel = int(df["Telefon"].astype(bool).sum())
    web = int(df["Web Sitesi"].astype(bool).sum())

    c1, c2, c3, c4 = st.columns(4)
    for col, num, lbl in zip([c1,c2,c3,c4], [len(df), ep, tel, web],
                              ["Toplam", "📧 E-posta", "📞 Telefon", "🌐 Web"]):
        with col:
            st.markdown(f'<div class="stat"><div class="stat-n">{num}</div>'
                        f'<div class="stat-l">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📊 Sonuçlar")

    c1, c2 = st.columns([3, 1])
    with c1:
        ara = st.text_input("🔍 Ara...", "", label_visibility="collapsed",
                             placeholder="Firma adı ara...")
    with c2:
        sadece = st.checkbox("Sadece bulunanlar")

    if ara:
        df = df[df.apply(lambda r: ara.lower() in str(r.values).lower(), axis=1)]
    if sadece:
        df = df[df["E-posta"].astype(bool) | df["Telefon"].astype(bool)]

    st.dataframe(df, use_container_width=True, height=400)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 💾 Dışa Aktar")
    dosya_adi = (sehir_input or "osb") + "_firmalar"

    c1, c2, c3 = st.columns(3)
    with c1:
        csv = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("📥 CSV İndir", csv, f"{dosya_adi}.csv",
                           "text/csv", use_container_width=True)
    with c2:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="Firmalar")
        st.download_button("📥 Excel İndir", buf.getvalue(), f"{dosya_adi}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)
    with c3:
        if st.button("🗑️ Sıfırla", use_container_width=True):
            for k in ["df_isimler", "df_iletisim", "loglar"]:
                st.session_state[k] = [] if k == "loglar" else None
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="text-align:center;padding:3rem;background:white;border-radius:12px;
                box-shadow:0 2px 10px rgba(0,0,0,.07);margin-top:1rem">
        <div style="font-size:4rem">🏭</div>
        <h3 style="color:#444;margin-top:1rem">Başlamak için:</h3>
        <p style="color:#888">1️⃣ OSB firma listesi URL'sini gir<br>
        2️⃣ <b>Çek</b> butonuna bas<br>
        3️⃣ İletişim aramasını başlat<br>
        4️⃣ Excel olarak indir</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;color:#aaa;font-size:.8rem;padding:1rem">
    OSB Firma Tarayıcı • DuckDuckGo + Web Scraping • Gumloop
</div>
""", unsafe_allow_html=True)
