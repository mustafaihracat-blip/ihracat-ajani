import streamlit as st
import anthropic
import time
from datetime import datetime

# ── Sayfa ayarları ──────────────────────────────────────────
st.set_page_config(
    page_title="İhracat İstihbarat Ajanı",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Stil ────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem; font-weight: 800;
        background: linear-gradient(135deg, #e8b84b, #e87b4b);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .subtitle { color: #888; font-size: 0.9rem; margin-bottom: 2rem; }
    .section-box {
        background: #1a1a24; border: 1px solid #2a2a38;
        border-radius: 8px; padding: 1.2rem; margin-bottom: 1rem;
    }
    .section-title {
        font-size: 1.1rem; font-weight: 700;
        color: #e8b84b; margin-bottom: 0.8rem;
    }
    .badge-ok   { background:#0d2818; color:#4be8a0; padding:2px 10px; border-radius:12px; font-size:0.75rem; }
    .badge-warn { background:#2a2000; color:#e8b84b; padding:2px 10px; border-radius:12px; font-size:0.75rem; }
    .badge-err  { background:#2a0000; color:#e84b4b; padding:2px 10px; border-radius:12px; font-size:0.75rem; }
    .step-running { color: #e8b84b; }
    .step-done    { color: #4be8a0; }
    .step-pending { color: #555; }
    div[data-testid="stExpander"] { border: 1px solid #2a2a38 !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ── Başlık ──────────────────────────────────────────────────
st.markdown('<div class="main-title">🌍 İhracat İstihbarat Ajanı</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Web sitesi analizi · GTİP tespiti · Pazar araştırması · Rakip karşılaştırması</div>', unsafe_allow_html=True)

# ── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Yapılandırma")

    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-...",
        help="console.anthropic.com adresinden ücretsiz alabilirsiniz"
    )

    st.divider()

    website_url = st.text_input(
        "🌐 Web Sitesi URL",
        placeholder="https://megates.com.tr",
        value="https://megates.com.tr"
    )

    target_market = st.text_input(
        "🎯 Hedef Pazar (opsiyonel)",
        placeholder="örn: Nijerya, Almanya, BAE"
    )

    comp_country = st.text_input(
        "🔍 Rakip Ülke (opsiyonel)",
        placeholder="boş bırakırsan ajan seçer"
    )

    st.divider()
    st.markdown("### 📦 Modüller")

    mod_web        = st.checkbox("🌐 Web Site Analizi (10 madde)", value=True)
    mod_gtip       = st.checkbox("📦 GTİP & Ürün Tespiti", value=True)
    mod_market     = st.checkbox("🌍 Pazar Analizi (3 Pazar)", value=True)
    mod_tariff     = st.checkbox("💰 Vergi & Tarife Analizi", value=True)
    mod_cert       = st.checkbox("📋 Sertifika & Belge Analizi", value=True)
    mod_logistics  = st.checkbox("🚢 Lojistik Analizi", value=True)
    mod_competitor = st.checkbox("⚔️ Rakip Analizi (10 Rakip)", value=True)

    st.divider()
    run_button = st.button("▶ Ajanı Başlat", type="primary", use_container_width=True)

# ── Promptlar ───────────────────────────────────────────────
def get_prompts(url, market, comp_country):
    m = market or "Nijerya, Almanya ve BAE"
    c = comp_country or market or "global"

    return {
        "web": f"""
{url} web sitesini analiz et. Aşağıdaki 10 maddenin HEPSİNİ Türkçe raporla:

1. **ÜRÜN ANALİZİ**: Sitedeki tüm ürünleri listele. Her ürün: ad, açıklama, teknik özellikler var mı?
2. **SERTİFİKALAR**: Hangi sertifikalar var (CE, ISO, IEC vb.)? Eksik olanlar neler?
3. **DİLLER**: Kaç dil var? İhracat için eksik diller?
4. **SOSYAL MEDYA**: Hangi hesaplar var? Aktif mi? Son paylaşım? Takipçi sayısı?
5. **ÇEVİRİ KALİTESİ**: İngilizce çeviriler doğru mu? Yanlış/eksik örnekler ver.
6. **SEO ANALİZİ**: Meta description, H1/H2, anahtar kelimeler, hız sorunları, eksikler.
7. **TEKNİK DOKÜMANLAR**: Katalog, şartname, kullanım kılavuzu var mı? Yeterli mi?
8. **GARANTİ KOŞULLARI**: Garanti bilgisi var mı? Süresi? Koşullar açık mı?
9. **TEKNİK DESTEK**: Teknik destek bölümü var mı? İletişim kanalları yeterli mi?
10. **GENEL EKSİKLİKLER**: Başka önemli eksiklikler neler? Rakiplerine göre ne eksik?

Her maddeyi başlık olarak yaz. Somut ve uygulanabilir öneriler ver.
""",
        "gtip": f"""
{url} sitesindeki ürünler için:

1. **GTİP NUMARALARI**: Her ürün kategorisi için GTİP (HS Code) numaralarını bul.
   Tablo: Ürün | GTİP Kodu | Açıklama

2. **TEKNİK DOKÜMANLARIN YETERLİLİĞİ**: İhracat için yeterli mi? Eksikler?

3. **GARANTİ KOŞULLARI**: Uluslararası standartlara uyuyor mu? Ne eksik?

4. **ÜRÜN SERTİFİKASYON EKSİKLERİ**: İhracat için hangi sertifikalar eksik?
   Hedef pazar: {m}
""",
        "market": f"""
{url} sitesindeki ürünler için en uygun 3 ihracat pazarını belirle.
{f"Öncelikli değerlendir: {market}" if market else "En uygun 3 pazarı sen seç."}

Her pazar için:
1. NEDEN BU PAZAR? (3-5 somut sebep)
2. PAZAR BÜYÜKLÜĞÜ (milyar $, büyüme oranı)
3. TALEP DURUMU (yüksek/orta/düşük + sebep)
4. TÜRK ÜRETİCİ AVANTAJI
5. RİSKLER (3 ana risk)
6. GİRİŞ STRATEJİSİ

Sonunda 3 pazarı karşılaştıran özet tablo yap.
""",
        "tariff": f"""
{url} sitesindeki ürünlerin GTİP kodlarına göre ithalat vergi analizi:
Pazarlar: {m}

Her pazar/ürün için:
1. GÜMRÜK VERGİSİ (%)
2. KDV/VAT (ithalatta uygulanan)
3. EK VERGİLER (antidamping vb.)
4. TOPLAM VERGİ YÜKÜ (%)
5. VERGİ MUAFİYETLERİ (Türkiye anlaşması var mı?)
6. GÜMRÜK PROSEDÜRÜ

Tablo formatında raporla.
""",
        "cert": f"""
{url} sitesindeki ürünler için gerekli sertifika ve belgeler:
Pazarlar: {m}

Her pazar için:
1. ZORUNLU SERTİFİKALAR (olmadan ürün giremez)
2. TAVSİYE EDİLEN SERTİFİKALAR
3. ÖZEL DENETİM GEREKSİNİMLERİ
4. SERTİFİKA ALMA SÜRESİ (kaç ay)
5. SERTİFİKA MALİYETİ (tahmini $)
6. AKREDİTE KURULUŞLAR
7. TÜRKİYE'DEN BAŞVURABİLECEK KURULUŞLAR (SGS, Bureau Veritas, TÜV vb.)
""",
        "logistics": f"""
{url} sitesindeki ürünler için lojistik analizi:
Pazarlar: {m}

Her güzergah için:
1. DENİZ YOLU: çıkış/varış limanı, süre, navlun maliyeti, avantaj/dezavantaj
2. KARA YOLU (mümkünse): güzergah, süre, maliyet
3. HAVA YOLU: süre ve maliyet (acil gönderiler için)
4. TAVSİYE: hangi mod, neden?
5. INCOTERMS ÖNERİSİ (FOB, CIF, DAP?)
6. SİGORTA gereksinimleri
7. GÜMRÜK KOLAYLIKLARI (TIR, ATA Carnet vb.)
""",
        "competitor": f"""
{url} firmasının ürünleri için {c} pazarında 10 rakip tespit et ve karşılaştır.

BÖLÜM 1 — RAKİP LİSTESİ:
Şirket adı | Ülke | Web sitesi | Tahmini pazar payı | Ana ürünler

BÖLÜM 2 — KARŞILAŞTIRMALI ANALİZ TABLOSU:
Kriter | Bizim Firma | En Güçlü Rakip
(Fiyat, kalite, sertifika, teslimat, teknik destek, dijital varlık, pazar deneyimi)

BÖLÜM 3 — ARTILARI VE EKSİLERİ:
✅ GÜÇLİ YÖNLER (en az 5 madde)
❌ ZAYİF YÖNLER (en az 5 madde)
🎯 FARKLILASTIRMA STRATEJİSİ

BÖLÜM 4 — STRATEJİK ÖNERİLER:
Rakiplere karşı kazanmak için 5 somut öneri.
"""
    }

# ── API çağrısı ──────────────────────────────────────────────
def run_module(client, prompt):
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}]
    )
    return "".join(b.text for b in response.content if hasattr(b, "text"))

# ── Rapor dışa aktarma ───────────────────────────────────────
def build_report(results, url):
    lines = [
        "═" * 60,
        "    İHRACAT İSTİHBARAT RAPORU",
        f"    {url}",
        f"    Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        "═" * 60,
    ]
    titles = {
        "web": "🌐 WEB SİTE ANALİZİ",
        "gtip": "📦 GTİP & ÜRÜN TESPİTİ",
        "market": "🌍 PAZAR ANALİZİ",
        "tariff": "💰 VERGİ & TARİFE",
        "cert": "📋 SERTİFİKA & BELGE",
        "logistics": "🚢 LOJİSTİK ANALİZİ",
        "competitor": "⚔️ RAKİP ANALİZİ",
    }
    for key, text in results.items():
        lines += ["", titles.get(key, key), "─" * 50, text, ""]
    return "\n".join(lines)

# ── Ana çalışma ──────────────────────────────────────────────
if run_button:
    if not api_key:
        st.error("⚠️ Lütfen sol panelden Anthropic API Key girin.")
        st.info("👉 console.anthropic.com adresinden ücretsiz alabilirsiniz. Yeni hesaplara $5 kredi veriliyor.")
        st.stop()

    if not website_url:
        st.error("⚠️ Lütfen analiz edilecek web sitesini girin.")
        st.stop()

    selected = {
        "web": mod_web, "gtip": mod_gtip, "market": mod_market,
        "tariff": mod_tariff, "cert": mod_cert,
        "logistics": mod_logistics, "competitor": mod_competitor
    }
    active = [k for k, v in selected.items() if v]

    if not active:
        st.error("⚠️ En az bir modül seçin.")
        st.stop()

    client = anthropic.Anthropic(api_key=api_key)
    prompts = get_prompts(website_url, target_market, comp_country)

    module_names = {
        "web": "🌐 Web Site Analizi",
        "gtip": "📦 GTİP & Ürün Tespiti",
        "market": "🌍 Pazar Analizi",
        "tariff": "💰 Vergi & Tarife",
        "cert": "📋 Sertifika & Belge",
        "logistics": "🚢 Lojistik Analizi",
        "competitor": "⚔️ Rakip Analizi",
    }

    st.markdown(f"### ⚡ Analiz Başladı — `{website_url}`")
    st.markdown(f"*{len(active)} modül çalışacak — tahmini süre: {len(active)*1} dakika*")
    st.divider()

    progress = st.progress(0)
    status_area = st.empty()
    results = {}

    for i, mod in enumerate(active):
        status_area.markdown(f"**⏳ Çalışıyor:** {module_names[mod]}...")
        try:
            result = run_module(client, prompts[mod])
            results[mod] = result

            with st.expander(f"✅ {module_names[mod]}", expanded=True):
                st.markdown(result)

        except Exception as e:
            results[mod] = f"Hata: {str(e)}"
            with st.expander(f"❌ {module_names[mod]} — Hata"):
                st.error(str(e))

        progress.progress((i + 1) / len(active))
        time.sleep(0.5)

    status_area.markdown("### ✅ Analiz Tamamlandı!")
    st.balloons()
    st.divider()

    # İndir butonu
    report_text = build_report(results, website_url)
    st.download_button(
        label="📄 Tam Raporu İndir (.txt)",
        data=report_text,
        file_name=f"ihracat-raporu-{datetime.now().strftime('%Y%m%d-%H%M')}.txt",
        mime="text/plain",
        use_container_width=True
    )

else:
    # Karşılama ekranı
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🌐 Web Site Analizi")
        st.markdown("""
- Tüm ürünler incelenir
- Sertifikalar kontrol edilir
- Dil ve çeviri kalitesi
- SEO eksikleri tespit edilir
- Sosyal medya durumu
- Teknik doküman yeterliliği
- Garanti ve destek kontrolü
        """)
        st.markdown("#### 📦 GTİP & Ürün")
        st.markdown("""
- Otomatik GTİP kodu tespiti
- Teknik doküman analizi
- Sertifikasyon eksikleri
        """)
        st.markdown("#### 🌍 Pazar & Vergi")
        st.markdown("""
- 3 hedef pazar önerisi
- İthalat vergi oranları
- Gerekli sertifikalar
- Lojistik karşılaştırması
        """)

    with col2:
        st.markdown("#### ⚔️ Rakip Analizi")
        st.markdown("""
- 10 rakip otomatik tespiti
- Karşılaştırmalı tablo
- Güçlü/zayıf yönler
- Farklılaştırma stratejisi
- 5 somut öneri
        """)
        st.info("""
**Nasıl kullanılır?**

1. Sol panelden API Key gir
2. Web sitesi URL'sini yaz
3. Hedef pazarı belirt (opsiyonel)
4. Modülleri seç
5. **▶ Ajanı Başlat** butonuna bas

Analiz tamamlandığında raporu `.txt` olarak indirebilirsin.
        """)
        st.warning("""
**Maliyet tahmini:**
- Her tam analiz (7 modül): ~$0.10
- 20 öğrenci × 5 analiz = ~$10
- Aylık 100 analiz = ~$10-15
        """)
