import streamlit as st
import anthropic
import openpyxl
import json
import time
import io

st.set_page_config(
    page_title="OSB Lead Generation Ajanı",
    page_icon="🏭",
    layout="wide"
)

st.markdown("""
<style>
.main-title { font-size: 1.8rem; font-weight: 800; color: #1F4E79; }
.step-badge { display: inline-block; background: #1F4E79; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; margin-bottom: 8px; }
.osb-card { background: #f0f4ff; border: 2px solid #d0d8f0; border-radius: 10px; padding: 16px; cursor: pointer; transition: all .2s; margin-bottom: 8px; }
.osb-card:hover { border-color: #1F4E79; }
.osb-card.selected { border-color: #1F4E79; background: #e0ebff; }
.stat-box { background: #f8f9fc; border-radius: 8px; padding: 14px; text-align: center; border: 1px solid #e0e4f0; }
.stat-val { font-size: 26px; font-weight: 800; color: #1F4E79; }
.stat-label { font-size: 11px; color: #666; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

# ============ SESSION STATE ============
if 'adim' not in st.session_state:
    st.session_state.adim = 1
if 'sehir' not in st.session_state:
    st.session_state.sehir = ''
if 'osblar' not in st.session_state:
    st.session_state.osblar = []
if 'secili_osb' not in st.session_state:
    st.session_state.secili_osb = None
if 'tum_firmalar' not in st.session_state:
    st.session_state.tum_firmalar = []
if 'gosterilen_ids' not in st.session_state:
    st.session_state.gosterilen_ids = set()
if 'excel_buffer' not in st.session_state:
    st.session_state.excel_buffer = None

# ============ SIDEBAR ============
with st.sidebar:
    st.markdown("### ⚙️ Ayarlar")
    api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
    st.divider()

    # Adım göstergesi
    st.markdown("### 📍 Adımlar")
    adimlar = ["1️⃣ Şehir Gir", "2️⃣ OSB Seç", "3️⃣ Firma Listesi", "4️⃣ Excel İndir"]
    for i, a in enumerate(adimlar, 1):
        if i < st.session_state.adim:
            st.markdown(f"✅ ~~{a}~~")
        elif i == st.session_state.adim:
            st.markdown(f"**▶ {a}**")
        else:
            st.markdown(f"⏳ {a}")

    st.divider()
    if st.button("🔄 Sıfırla", use_container_width=True):
        for key in ['adim', 'sehir', 'osblar', 'secili_osb', 'tum_firmalar', 'gosterilen_ids', 'excel_buffer']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# ============ BAŞLIK ============
st.markdown('<div class="main-title">🏭 OSB Lead Generation Ajanı</div>', unsafe_allow_html=True)
st.markdown("---")

# ============ ADIM 1: ŞEHİR GİR ============
if st.session_state.adim == 1:
    st.markdown('<div class="step-badge">ADIM 1 / 4</div>', unsafe_allow_html=True)
    st.markdown("### 🏙️ Hangi şehrin OSB'lerini aratalım?")

    col1, col2 = st.columns([3, 1])
    with col1:
        sehir_input = st.text_input(
            "Şehir adı",
            placeholder="örn: Gaziantep, Bursa, Konya, İzmir...",
            label_visibility="collapsed"
        )
    with col2:
        ara_btn = st.button("🔍 OSB'leri Bul", type="primary", use_container_width=True)

    if ara_btn:
        if not api_key:
            st.error("⚠️ Sol panelden API Key gir!")
            st.stop()
        if not sehir_input:
            st.error("⚠️ Şehir adı gir!")
            st.stop()

        with st.spinner(f"{sehir_input} OSB'leri aranıyor..."):
            client = anthropic.Anthropic(api_key=api_key)

            r = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                messages=[{"role": "user", "content": f"""
{sehir_input} iline bağlı TÜM Organize Sanayi Bölgelerini (OSB) listele.
İlçelerdekiler dahil HEPSİNİ yaz. Hiçbirini atlama.

Sadece JSON döndür, başka hiçbir şey yazma:
{{
  "osblar": [
    {{
      "id": 1,
      "ad": "OSB tam adı",
      "website": "website veya null",
      "firma_sayisi": 150,
      "sektorler": ["tekstil", "metal"],
      "adres": "ilçe adı"
    }}
  ]
}}
"""}]
            )

            try:
                text = r.content[0].text
                clean = text[text.find('{'):text.rfind('}')+1]
                data = json.loads(clean)
                osblar = data.get('osblar', [])
                for i, o in enumerate(osblar):
                    o['id'] = i
            except:
                osblar = [{"id": 0, "ad": f"{sehir_input} OSB", "website": None, "firma_sayisi": 100, "sektorler": ["Karma"], "adres": "Merkez"}]

            st.session_state.sehir = sehir_input
            st.session_state.osblar = osblar
            st.session_state.adim = 2
            st.rerun()

# ============ ADIM 2: OSB SEÇ ============
elif st.session_state.adim == 2:
    st.markdown('<div class="step-badge">ADIM 2 / 4</div>', unsafe_allow_html=True)
    st.markdown(f"### 🏭 {st.session_state.sehir} — Hangi OSB'yi listeleyelim?")
    st.markdown(f"*{len(st.session_state.osblar)} OSB bulundu. Birini seç:*")
    st.markdown("")

    for osb in st.session_state.osblar:
        col1, col2 = st.columns([4, 1])
        with col1:
            sektorler = ', '.join(osb.get('sektorler', [])[:3])
            website = osb.get('website', '')
            web_html = f"&nbsp;|&nbsp; 🌐 {website}" if website else ''
            st.markdown(f"""
            <div class="osb-card">
                <strong style="font-size:15px; color:#1F4E79">{osb['ad']}</strong><br>
                <span style="font-size:12px; color:#666">
                    📍 {osb.get('adres', '-')} &nbsp;|&nbsp;
                    🏭 ~{osb.get('firma_sayisi', '?')} firma &nbsp;|&nbsp;
                    🔧 {sektorler}{web_html}
                </span>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            if st.button(f"Seç →", key=f"osb_{osb['id']}", use_container_width=True):
                st.session_state.secili_osb = osb
                st.session_state.tum_firmalar = []
                st.session_state.gosterilen_ids = set()
                st.session_state.adim = 3
                st.rerun()

    st.markdown("")
    if st.button("← Geri", use_container_width=False):
        st.session_state.adim = 1
        st.rerun()

# ============ ADIM 3: FİRMA LİSTESİ ============
elif st.session_state.adim == 3:
    st.markdown('<div class="step-badge">ADIM 3 / 4</div>', unsafe_allow_html=True)

    osb = st.session_state.secili_osb
    toplam_firma = osb.get('firma_sayisi', 100)
    gosterilen = len(st.session_state.gosterilen_ids)

    st.markdown(f"### 🔍 {osb['ad']} — Firma Listesi")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="stat-box"><div class="stat-val">{toplam_firma}</div><div class="stat-label">Tahmini Firma</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-box"><div class="stat-val">{len(st.session_state.tum_firmalar)}</div><div class="stat-label">Listelenen</div></div>', unsafe_allow_html=True)
    with col3:
        kalan = max(0, toplam_firma - gosterilen)
        st.markdown(f'<div class="stat-box"><div class="stat-val">{kalan}</div><div class="stat-label">Kalan Firma</div></div>', unsafe_allow_html=True)

    st.markdown("")

    # Kaç firma getirsin
    col_a, col_b = st.columns([2, 1])
    with col_a:
        adet = st.slider(
            "Kaç firma listeleyelim?",
            min_value=10,
            max_value=100,
            value=50,
            step=10
        )
    with col_b:
        email_ara = st.checkbox("📧 Email ara", value=True)

    listele_btn = st.button(
        f"📋 {adet} Firma Listele",
        type="primary",
        use_container_width=True,
        disabled=(gosterilen >= toplam_firma)
    )

    if listele_btn:
        if not api_key:
            st.error("⚠️ API Key gir!")
            st.stop()

        client = anthropic.Anthropic(api_key=api_key)

        with st.spinner(f"{adet} firma listeleniyor..."):

            # Daha önce gösterilenleri hariç tut
            gosterilen_adlar = [f['ad'] for f in st.session_state.tum_firmalar]
            haric = json.dumps(gosterilen_adlar[:50], ensure_ascii=False) if gosterilen_adlar else "[]"

            r = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=3000,
                messages=[{"role": "user", "content": f"""
{st.session_state.sehir} {osb['ad']} bünyesindeki firmaları listele.

ÖNEMLİ: Bu firmalar listede OLMAMALI (zaten gösterdik):
{haric}

Yukarıdakilerin DIŞINDA {adet} farklı firma listele.
Gerçek firma adları ver.

JSON:
{{
  "firmalar": [
    {{
      "ad": "firma adı",
      "website": "website veya null",
      "email": "email veya null",
      "telefon": "telefon veya null",
      "sektor": "sektör",
      "urunler": "ana ürünler"
    }}
  ]
}}
"""}]
            )

            try:
                text = r.content[0].text
                clean = text[text.find('{'):text.rfind('}')+1]
                data = json.loads(clean)
                yeni_firmalar = data.get('firmalar', [])
            except:
                yeni_firmalar = []

        # Email ara
        if email_ara and yeni_firmalar:
            progress_bar = st.progress(0)
            eksik = [f for f in yeni_firmalar if not f.get('email')]

            for i, firma in enumerate(eksik[:30]):
                progress_bar.progress(int(100 * i / max(len(eksik[:30]), 1)))

                r2 = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=150,
                    messages=[{"role": "user", "content": f"""
{firma['ad']} firmasının iletişim bilgilerini bul.
Şehir: {st.session_state.sehir}
Sektör: {firma.get('sektor', '')}

JSON: {{"email": "email veya null", "telefon": "telefon veya null", "kaynak": "kaynak"}}
"""}]
                )

                try:
                    i_text = r2.content[0].text
                    i_clean = i_text[i_text.find('{'):i_text.rfind('}')+1]
                    iletisim = json.loads(i_clean)
                    if iletisim.get('email') and not firma.get('email'):
                        firma['email'] = iletisim['email']
                        firma['kaynak'] = iletisim.get('kaynak', 'Web')
                    if iletisim.get('telefon') and not firma.get('telefon'):
                        firma['telefon'] = iletisim['telefon']
                except:
                    pass

                time.sleep(0.2)

            progress_bar.empty()

        # Listeye ekle
        for f in yeni_firmalar:
            f['osb'] = osb['ad']
            f['sehir'] = st.session_state.sehir
            st.session_state.tum_firmalar.append(f)
            st.session_state.gosterilen_ids.add(f['ad'])

        st.rerun()

    # Firma tablosu göster
    if st.session_state.tum_firmalar:
        st.markdown("---")
        st.markdown(f"**📋 Listelenen Firmalar ({len(st.session_state.tum_firmalar)} adet)**")

        for i, f in enumerate(st.session_state.tum_firmalar):
            email = f.get('email', '')
            tel = f.get('telefon', '')

            if email and tel:
                renk = "#E1F5EE"
                durum = "✅"
            elif email or tel:
                renk = "#FAEEDA"
                durum = "⚠️"
            else:
                renk = "#FCEBEB"
                durum = "❌"

            st.markdown(f"""
            <div style="background:{renk}; border-radius:6px; padding:10px 14px; margin-bottom:6px; font-size:13px;">
                {durum} <strong>{f['ad']}</strong> &nbsp;|&nbsp; 
                🔧 {f.get('sektor', '-')} &nbsp;|&nbsp;
                📧 {email or '—'} &nbsp;|&nbsp;
                📞 {tel or '—'} &nbsp;|&nbsp;
                🌐 {f.get('website', '—')}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")
        col_x, col_y = st.columns(2)
        with col_x:
            if st.button("⬇️ Excel'e Aktar", type="primary", use_container_width=True):
                st.session_state.adim = 4
                st.rerun()
        with col_y:
            if st.button("← OSB Seçimine Dön", use_container_width=True):
                st.session_state.adim = 2
                st.rerun()

# ============ ADIM 4: EXCEL İNDİR ============
elif st.session_state.adim == 4:
    st.markdown('<div class="step-badge">ADIM 4 / 4</div>', unsafe_allow_html=True)
    st.markdown("### 📊 Excel Dosyası Hazırlanıyor...")

    firmalar = st.session_state.tum_firmalar

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{st.session_state.sehir} OSB"

    basliklar = ["#", "Firma Adı", "OSB", "Sektör", "Web Sitesi", "Email", "Telefon", "Ürünler", "Durum"]
    for col, b in enumerate(basliklar, 1):
        h = ws.cell(row=1, column=col, value=b)
        h.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
        h.fill = openpyxl.styles.PatternFill("solid", fgColor="1F4E79")
        h.alignment = openpyxl.styles.Alignment(horizontal="center")

    tam = kismi = eksik_count = 0

    for row, f in enumerate(firmalar, 2):
        email = f.get('email', '')
        tel = f.get('telefon', '')

        if email and tel:
            durum = "✅ Tam"
            renk = "E1F5EE"
            tam += 1
        elif email or tel:
            durum = "⚠️ Kısmi"
            renk = "FAEEDA"
            kismi += 1
        else:
            durum = "❌ Manuel"
            renk = "FCEBEB"
            eksik_count += 1

        ws.cell(row=row, column=1, value=row-1)
        ws.cell(row=row, column=2, value=f.get('ad', ''))
        ws.cell(row=row, column=3, value=f.get('osb', ''))
        ws.cell(row=row, column=4, value=f.get('sektor', ''))
        ws.cell(row=row, column=5, value=f.get('website', ''))
        ws.cell(row=row, column=6, value=email)
        ws.cell(row=row, column=7, value=tel)
        ws.cell(row=row, column=8, value=f.get('urunler', ''))
        d = ws.cell(row=row, column=9, value=durum)
        d.fill = openpyxl.styles.PatternFill("solid", fgColor=renk)

    for col in ws.columns:
        w = max(len(str(c.value or '')) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(w + 4, 35)

    # Özet sayfası
    ws2 = wb.create_sheet("Özet")
    ws2['A1'] = f"{st.session_state.sehir} OSB Lead Listesi"
    ws2['A1'].font = openpyxl.styles.Font(bold=True, size=14, color="1F4E79")
    ws2['A3'] = "Toplam Firma"
    ws2['B3'] = len(firmalar)
    ws2['A4'] = "✅ Tam İletişim"
    ws2['B4'] = tam
    ws2['A5'] = "⚠️ Kısmi"
    ws2['B5'] = kismi
    ws2['A6'] = "❌ Manuel Kontrol"
    ws2['B6'] = eksik_count
    ws2['A7'] = "Email Bulma Oranı"
    ws2['B7'] = f"%{int((tam + kismi) / len(firmalar) * 100) if firmalar else 0}"

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    # İstatistikler
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-box"><div class="stat-val">{len(firmalar)}</div><div class="stat-label">Toplam</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-box"><div class="stat-val" style="color:#1a7a4a">{tam}</div><div class="stat-label">✅ Tam</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-box"><div class="stat-val" style="color:#BA7517">{kismi}</div><div class="stat-label">⚠️ Kısmi</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-box"><div class="stat-val" style="color:#c8401a">{eksik_count}</div><div class="stat-label">❌ Manuel</div></div>', unsafe_allow_html=True)

    st.markdown("")
    st.download_button(
        label=f"⬇️ {st.session_state.sehir}_OSB_Firma_Listesi.xlsx İndir",
        data=buffer,
        file_name=f"{st.session_state.sehir}_OSB_Firma_Listesi.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    st.markdown("")
    col_p, col_q = st.columns(2)
    with col_p:
        if st.button("➕ Daha Fazla Firma Ekle", use_container_width=True):
            st.session_state.adim = 3
            st.rerun()
    with col_q:
        if st.button("🔄 Yeni Şehir", use_container_width=True):
            for key in ['adim', 'sehir', 'osblar', 'secili_osb', 'tum_firmalar', 'gosterilen_ids']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    st.balloons()
