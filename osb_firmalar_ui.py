import streamlit as st
import pandas as pd
import openpyxl
import io
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin
import time

st.set_page_config(page_title="OSB Firma Tarayıcı", page_icon="🏭", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; }
    .hero { background: linear-gradient(135deg,#1F4E79,#2e86de); border-radius:16px;
            padding:2rem 2.5rem; color:white; margin-bottom:1.5rem; }
    .hero h1 { font-size:2rem; margin:0; }
    .hero p  { margin:.5rem 0 0; opacity:.85; }
    .card { background:white; border-radius:12px; padding:1.5rem;
            box-shadow:0 2px 10px rgba(0,0,0,.07); margin-bottom:1.2rem; }
    .stat { background:white; border-radius:12px; padding:1.2rem;
            text-align:center; box-shadow:0 2px 10px rgba(0,0,0,.07); }
    .stat-n { font-size:2rem; font-weight:700; color:#1F4E79; }
    .stat-l { font-size:.82rem; color:#666; }
    .stButton>button { background:linear-gradient(135deg,#2e86de,#1F4E79);
        color:white; border:none; border-radius:8px; font-weight:600; width:100%; }
</style>
""", unsafe_allow_html=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ── Yardımcılar ───────────────────────────────────────────────────────────────
def temizle(t): return re.sub(r"\s+", " ", str(t)).strip()

def email_bul(html):
    for a in BeautifulSoup(str(html), "html.parser").select("a[href^=mailto]"):
        ep = a["href"].replace("mailto:","").split("?")[0].strip()
        if "@" in ep: return ep
    m = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]{2,}", str(html))
    return m[0] if m else ""

def tel_bul(metin):
    m = re.findall(r"(\+90|0)[\s\-\(\)]?\d{3}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}", str(metin))
    return m[0].strip() if m else ""

def web_bul(html, ana_domain):
    soup = BeautifulSoup(str(html), "html.parser")
    for a in soup.select("a[href]"):
        h = a.get("href","")
        if h.startswith("http") and ana_domain not in h and re.match(r"https?://[\w.-]+\.[a-z]{2,}", h):
            return h
    return ""

def get(url, timeout=12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.encoding = r.apparent_encoding
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser"), None
    except Exception as e:
        return None, str(e)

# ── Site Kara Listesi ─────────────────────────────────────────────────────────
def kara_listesi_cek(ana_url):
    soup, _ = get(ana_url)
    kara_ep, kara_tel = [], []
    ana_domain = urlparse(ana_url).netloc.replace("www.","")
    if soup:
        for a in soup.select("a[href^=mailto]"):
            ep = a["href"].replace("mailto:","").split("?")[0].lower()
            if "@" in ep: kara_ep.append(ep.split("@")[1])
        footer = soup.select_one("footer,.footer,#footer")
        if footer:
            for t in re.findall(r"(\+90|0)\d[\d\s\-]{9,}", footer.get_text()):
                kara_tel.append(re.sub(r"\D","",t)[:7])
    kara_ep.append(ana_domain)
    return list(set(kara_ep)), list(set(kara_tel))

# ── Firma Listesini Çek ───────────────────────────────────────────────────────
def firma_listesi_cek(url, kara_ep, kara_tel):
    soup, hata = get(url)
    if not soup: return [], [], hata
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    ana_domain = urlparse(url).netloc.replace("www.","")
    firmalar = []

    # Tablo
    for tablo in soup.select("table"):
        satirlar = tablo.select("tr")
        if len(satirlar) < 3: continue
        basliklar = [temizle(h.get_text()) for h in satirlar[0].select("th,td")]
        for satir in satirlar[1:]:
            hucreler = satir.select("td")
            if not hucreler: continue
            ad = temizle(hucreler[0].get_text())
            if len(ad) < 3 or re.search(r"\d{4}",ad): continue
            a_tag = hucreler[0].select_one("a[href]")
            detay = urljoin(base, a_tag["href"]) if a_tag else ""
            if "iletisim" in detay: continue
            firma = {"Firma Adı": ad, "_detay": detay, "E-posta":"", "Telefon":"", "Web Sitesi":"", "Adres":""}
            for i,bsl in enumerate(basliklar[1:],1):
                if i < len(hucreler):
                    firma[bsl if bsl else f"Alan{i}"] = temizle(hucreler[i].get_text())
            firmalar.append(firma)
        if firmalar: break

    # Kart/liste
    if not firmalar:
        for sel in ["[class*=firma]","[class*=uye]","[class*=member]","[class*=company]","li"]:
            kartlar = soup.select(sel)
            if len(kartlar) < 3: continue
            for k in kartlar:
                ad_el = k.select_one("h1,h2,h3,h4,strong,.title")
                ad = temizle(ad_el.get_text()) if ad_el else temizle(k.get_text())[:80]
                if len(ad) < 3 or re.search(r"\d{4}",ad): continue
                a_tag = k.select_one("a[href]")
                detay = urljoin(base, a_tag["href"]) if a_tag and a_tag.get("href") else ""
                if "iletisim" in detay: continue
                ep = email_bul(str(k))
                if any(kara in ep for kara in kara_ep): ep = ""
                firmalar.append({"Firma Adı":ad,"_detay":detay,"E-posta":ep,
                                  "Telefon":tel_bul(k.get_text()),"Web Sitesi":"","Adres":""})
            if firmalar: break

    # Sayfalama
    sonraki = []
    for a in soup.select("a[href]"):
        href = a.get("href",""); metin = a.get_text(strip=True).lower()
        if re.search(r"page[=/]\d+|sayfa[=/]\d+|\bsonraki\b|\bnext\b|»", metin+href, re.I):
            t = urljoin(base,href)
            if t != url: sonraki.append(t)
    return firmalar, list(set(sonraki))[:8], None

# ── Detay Sayfasından İletişim ────────────────────────────────────────────────
def detay_cek(url, kara_ep, kara_tel, ana_domain):
    soup, _ = get(url)
    if not soup: return {}
    ep = email_bul(soup)
    if any(kara in ep for kara in kara_ep): ep = ""
    tel_ham = tel_bul(soup.get_text())
    tel = "" if any(kara in re.sub(r"\D","",tel_ham)[:7] for kara in kara_tel) else tel_ham
    web = web_bul(soup, ana_domain)
    adres = ""
    for tag in soup.select("p,td,.adres,.address"):
        t = temizle(tag.get_text())
        if re.search(r"(osb|cad\.|sok\.|mah\.|organize sanayi)", t, re.I) and 15 < len(t) < 200:
            adres = t; break
    return {"E-posta":ep,"Telefon":tel,"Web Sitesi":web,"Adres":adres}

# ── Session State ─────────────────────────────────────────────────────────────
for k,v in [("df",None),("loglar",[]),("bitti",False)]:
    if k not in st.session_state: st.session_state[k] = v

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🏭 OSB Firma Tarayıcı</h1>
  <p>API key gerekmez &nbsp;•&nbsp; Direkt OSB sitesini tarar &nbsp;•&nbsp; E-posta & telefon çeker &nbsp;•&nbsp; Excel indir</p>
</div>""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Ayarlar")
    st.markdown("---")
    max_sayfa  = st.slider("Firma listesi sayfası", 1, 20, 5)
    detay_ac   = st.toggle("🔍 Detay sayfalarını tara", True)
    max_detay  = st.slider("Max detay", 10, 500, 100, 10, disabled=not detay_ac)
    gecikme    = st.select_slider("Gecikme (sn)", [0.2,0.5,1.0,1.5], value=0.5)
    st.markdown("---")
    st.success("✅ API key gerekmez!\nSadece OSB sitesinin URL'sini gir.")

# ── URL Girişi ────────────────────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### 🔗 OSB Firma Listesi URL'si")
st.caption("Direkt firma listesi sayfasını gir")
c1,c2 = st.columns([4,1])
with c1:
    url_in = st.text_input("","",placeholder="https://www.iaosb.org.tr/uyefirmalar",
                            label_visibility="collapsed")
with c2:
    btn = st.button("🚀 Tara", use_container_width=True)
ad = st.text_input("Kayıt adı (Excel dosyası için)","", placeholder="izmir_ataturk_osb")
st.markdown("</div>", unsafe_allow_html=True)

# ── İstatistikler ─────────────────────────────────────────────────────────────
df_s = st.session_state.df
top  = len(df_s) if df_s is not None else 0
ep   = int(df_s["E-posta"].astype(bool).sum())    if df_s is not None and "E-posta"    in df_s.columns else 0
tel  = int(df_s["Telefon"].astype(bool).sum())    if df_s is not None and "Telefon"    in df_s.columns else 0
web  = int(df_s["Web Sitesi"].astype(bool).sum()) if df_s is not None and "Web Sitesi" in df_s.columns else 0

cols = st.columns(4)
for col,num,lbl in zip(cols,[top,ep,tel,web],["Toplam Firma","📧 E-posta","📞 Telefon","🌐 Web"]):
    with col:
        st.markdown(f'<div class="stat"><div class="stat-n">{num}</div>'
                    f'<div class="stat-l">{lbl}</div></div>', unsafe_allow_html=True)
st.markdown("<br>",unsafe_allow_html=True)

# ── Tarama ────────────────────────────────────────────────────────────────────
if btn:
    if not url_in.strip():
        st.warning("URL girin!")
    else:
        st.session_state.df = None
        st.session_state.loglar = []
        st.session_state.bitti = False

        prog  = st.progress(0)
        durum = st.empty()
        log_e = st.empty()

        ana_domain = urlparse(url_in).netloc.replace("www.","")
        durum.info("🔍 Site analiz ediliyor...")
        kara_ep, kara_tel = kara_listesi_cek(url_in.strip())
        loglar = [f"🚫 Kara liste: {kara_ep[:3]}"]

        # Liste sayfaları
        tum_firmalar, kuyruk, ziyaret = [], [url_in.strip()], set()
        sayfa = 0
        while kuyruk and sayfa < max_sayfa:
            url = kuyruk.pop(0)
            if url in ziyaret: continue
            ziyaret.add(url); sayfa += 1
            durum.info(f"📋 Sayfa {sayfa} çekiliyor...")
            firmalar, sonraki, hata = firma_listesi_cek(url, kara_ep, kara_tel)
            if hata: loglar.append(f"❌ S{sayfa}: {hata}")
            else:
                loglar.append(f"✅ S{sayfa}: {len(firmalar)} firma")
                tum_firmalar.extend(firmalar)
                for s in sonraki:
                    if s not in ziyaret: kuyruk.append(s)
            log_e.code("\n".join(loglar[-8:]))
            prog.progress(min(30, sayfa*6))
            time.sleep(gecikme)

        # Tekrar kaldır
        goruldu, benzersiz = set(), []
        for f in tum_firmalar:
            if f["Firma Adı"] not in goruldu:
                goruldu.add(f["Firma Adı"]); benzersiz.append(f)
        tum_firmalar = benzersiz
        loglar.append(f"📊 {len(tum_firmalar)} benzersiz firma")

        # Detay sayfaları
        ep_say = 0
        if detay_ac and tum_firmalar:
            sinir = min(max_detay, len(tum_firmalar))
            for i, f in enumerate(tum_firmalar[:sinir]):
                detay_url = f.get("_detay","").strip()
                if not detay_url or "iletisim" in detay_url: continue
                ile = detay_cek(detay_url, kara_ep, kara_tel, ana_domain)
                for k,v in ile.items():
                    if v and not f.get(k): f[k] = v
                if f.get("E-posta"): ep_say += 1
                pct = 30 + int((i/sinir)*65)
                prog.progress(min(95,pct))
                if (i+1) % 10 == 0:
                    loglar.append(f"  🔍 {i+1}/{sinir} detay — {ep_say} e-posta")
                    log_e.code("\n".join(loglar[-8:]))
                time.sleep(gecikme)
            loglar.append(f"✅ Detay bitti: {ep_say} e-posta")

        for f in tum_firmalar: f.pop("_detay", None)

        st.session_state.df    = pd.DataFrame(tum_firmalar)
        st.session_state.loglar = loglar
        st.session_state.bitti = True
        prog.progress(100)

        if len(tum_firmalar) > 0:
            durum.success(f"🎉 Tamamlandı! {len(tum_firmalar)} firma, {ep_say} e-posta bulundu.")
        else:
            durum.error("❌ Firma bulunamadı. URL'yi kontrol et.")
        st.rerun()

# ── Log ───────────────────────────────────────────────────────────────────────
if st.session_state.loglar:
    with st.expander("📋 Loglar"):
        st.code("\n".join(st.session_state.loglar))

# ── Tablo ─────────────────────────────────────────────────────────────────────
if st.session_state.df is not None and len(st.session_state.df) > 0:
    df = st.session_state.df.copy()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📊 Firma Listesi")
    c1,c2,c3 = st.columns([3,1,1])
    with c1:
        ara = st.text_input("🔍","", placeholder="Ara...", label_visibility="collapsed")
    with c2:
        sc = next((s for s in df.columns if "sekt" in s.lower()),None)
        if sc:
            sl = ["Tümü"]+sorted(df[sc].dropna().unique().tolist())
            ss = st.selectbox("Sektör",sl)
        else: ss = "Tümü"
    with c3:
        sep = st.checkbox("Sadece e-postalılar")

    if ara: df = df[df.apply(lambda r: ara.lower() in str(r.values).lower(), axis=1)]
    if ss != "Tümü" and sc: df = df[df[sc]==ss]
    if sep and "E-posta" in df.columns: df = df[df["E-posta"].astype(bool)]

    st.dataframe(df, use_container_width=True, height=420)
    st.markdown("</div>", unsafe_allow_html=True)

    # İndir
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 💾 Dışa Aktar")
    dosya = ad or "osb_firmalar"
    c1,c2,c3 = st.columns(3)
    with c1:
        csv = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("📥 CSV", csv, f"{dosya}.csv", "text/csv", use_container_width=True)
    with c2:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="Firmalar")
        st.download_button("📥 Excel", buf.getvalue(), f"{dosya}.xlsx",
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
                box-shadow:0 2px 10px rgba(0,0,0,.07)">
        <div style="font-size:4rem">🏭</div>
        <h3 style="color:#444;margin-top:1rem">Hazır</h3>
        <p style="color:#888">OSB firma listesi URL'sini gir → <b>Tara</b></p>
        <p style="color:#aaa;font-size:.85rem">Örn: https://www.iaosb.org.tr/uyefirmalar</p>
    </div>""", unsafe_allow_html=True)

st.markdown("""<div style="text-align:center;color:#aaa;font-size:.8rem;padding:1rem">
OSB Firma Tarayıcı • Gumloop</div>""", unsafe_allow_html=True)
