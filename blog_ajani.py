"""
====================================================
  KURS DEĞİL KARİYER — OTOMATİK BLOG AJANI
  Her gün 1 SEO uyumlu blog yazısı yayınlar.
====================================================
"""

import requests
import base64
import os
import json
from datetime import datetime

# ─── AYARLAR (GitHub Secrets'tan gelir) ─────────────────
WP_URL            = os.environ.get("WP_URL", "https://www.kursdegilkariyer.online")
WP_USER           = os.environ.get("WP_USER", "yz")
WP_APP_PASSWORD   = os.environ.get("WP_APP_PASSWORD", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ─── KONU HAVUZU ─────────────────────────────────────────
KONULAR = [
    {"baslik": "Uluslararası İlişkiler Mezunları İçin İş İmkanları",                   "seo": "uluslararası ilişkiler mezunları iş imkanları"},
    {"baslik": "Uluslararası İlişkiler Bölümü Dış Ticaret Kariyeri",                   "seo": "uluslararası ilişkiler dış ticaret kariyer"},
    {"baslik": "Uluslararası İlişkiler İçin Maaş Garantili İşler",                     "seo": "uluslararası ilişkiler maaş garantili iş"},
    {"baslik": "Uluslararası İlişkiler Son Sınıf Staj ve İş Fırsatları",               "seo": "uluslararası ilişkiler son sınıf staj iş"},
    {"baslik": "Uluslararası İlişkiler Öğrencileri İçin İhracat Eğitimi",              "seo": "uluslararası ilişkiler ihracat eğitimi"},
    {"baslik": "Uluslararası İlişkiler Mezunu Nasıl İhracat Uzmanı Olur",              "seo": "uluslararası ilişkiler ihracat uzmanı nasıl olunur"},
    {"baslik": "Uluslararası İlişkiler Kariyer Basamakları ve Maaşlar",                "seo": "uluslararası ilişkiler kariyer maaş"},
    {"baslik": "Uluslararası İlişkiler ve Yapay Zeka ile Dış Ticaret",                 "seo": "uluslararası ilişkiler yapay zeka dış ticaret"},
    {"baslik": "Uluslararası İlişkiler Bölümü Özel Sektör Pozisyonları",               "seo": "uluslararası ilişkiler özel sektör iş"},
    {"baslik": "Uluslararası İlişkiler Diploması ile Global Ticaret",                  "seo": "uluslararası ilişkiler global ticaret kariyer"},
    {"baslik": "Uluslararası İlişkiler Mezunu Dış Ticaret Uzmanı Maaşı",               "seo": "dış ticaret uzmanı maaş uluslararası ilişkiler"},
    {"baslik": "İhracat Uzmanı Olmak İçin Hangi Eğitim Gerekir",                       "seo": "ihracat uzmanı eğitim sertifika"},
    {"baslik": "Uluslararası İlişkiler Mezunu Yurt Dışında Çalışma",                   "seo": "uluslararası ilişkiler yurt dışı iş imkanı"},
    {"baslik": "Dış Ticaret Kariyerinde İlk 1 Yıl Nasıl Geçer",                       "seo": "dış ticaret uzmanı ilk iş deneyimi"},
    {"baslik": "Uluslararası İlişkiler Öğrencisi İçin Dış Ticaret Stajı",             "seo": "uluslararası ilişkiler dış ticaret staj"},
    {"baslik": "Türkiye İhracat Sektöründe Kariyer Fırsatları",                        "seo": "türkiye ihracat kariyer fırsatları"},
    {"baslik": "Yabancı Dil Bilen Uluslararası İlişkiler Mezunu Ne İş Yapar",         "seo": "yabancı dil dış ticaret iş imkanı"},
    {"baslik": "Dış Ticarette Yapay Zeka Araçlarını Kullanan Uzman Olmak",             "seo": "yapay zeka dış ticaret ihracat araçları"},
    {"baslik": "Uluslararası İlişkiler Mezunu Freelance Dış Ticaret Danışmanı",        "seo": "dış ticaret danışmanı freelance kariyer"},
    {"baslik": "B2B Sistemleri ile Yurt Dışı Müşteri Bulma Rehberi",                   "seo": "b2b yurt dışı müşteri bulma ihracat"},
    {"baslik": "Uluslararası İlişkiler Bölümü Gerçekten İşe Yarar mı",                "seo": "uluslararası ilişkiler bölümü iş bulma"},
    {"baslik": "KPSS Yerine Dış Ticaret: Uluslararası İlişkiler Mezununa Gerçek Yol", "seo": "kpss yerine dış ticaret kariyer uluslararası ilişkiler"},
    {"baslik": "İhracatta Müzakere Sanatı ve Uluslararası İlişkiler Avantajı",         "seo": "ihracat müzakere uluslararası ilişkiler avantaj"},
    {"baslik": "Dış Ticaret Uzmanı Olarak Uzaktan Çalışmak Mümkün mü",               "seo": "dış ticaret uzmanı uzaktan çalışma remote"},
    {"baslik": "Uluslararası İlişkiler ve Lojistik: Kariyer Kesişim Noktaları",        "seo": "uluslararası ilişkiler lojistik kariyer"},
    {"baslik": "Kültürel Zeka: Uluslararası İlişkiler Mezununun Gizli Silahı",         "seo": "kültürel zeka dış ticaret kariyer avantaj"},
    {"baslik": "Afrika Pazarına İhracat: Uluslararası İlişkiler Fırsatları",           "seo": "afrika ihracat kariyer uluslararası ilişkiler"},
    {"baslik": "Orta Doğu Ticaretinde Kariyer: Dil ve Kültür Bilen Uzmanlar",         "seo": "orta doğu ticaret kariyer uluslararası ilişkiler"},
    {"baslik": "Türkiye'den Avrupa'ya İhracat: Genç Uzmanlar İçin Kariyer",            "seo": "avrupa ihracat kariyer türkiye genç uzman"},
    {"baslik": "LinkedIn ile Yurt Dışı İş Bağlantısı Kurma Rehberi",                  "seo": "linkedin yurt dışı iş bağlantı uluslararası ilişkiler"},
]


def bugunun_konusunu_sec():
    gun = (datetime.now() - datetime(2025, 1, 1)).days % len(KONULAR)
    return KONULAR[gun]


def claude_ile_yazi_olustur(konu):
    print(f"🤖 Claude yazıyor: {konu['baslik']}")

    sistem = """Sen kursdegilkariyer.online için Türkçe SEO blog yazıları yazan uzmansın.
Site sahibi: Mustafa Hoca — 25+ yıllık dış ticaret eğitmeni.
Program özeti: Öğrenci eğitim alır → işe girer → eğitim ücretinin sadece %40'ını öder. İşe giremezse hiç ödemez.

HEDEF KİTLE: 20-26 yaş, üniversite son sınıf veya yeni mezun uluslararası ilişkiler öğrencisi/mezunu.
Bu kişinin kafasındaki soru: "Bu bölümü okuyunca ne iş yapacağım?"

YAZI KURALLARI:
- Ton: Samimi, motive edici, arkadaşça — ama olgun ve profesyonel. Abartma yok.
- Uzunluk: 3-4 güçlü paragraf. Çok uzun olmasın.
- Mesaj: Uluslararası ilişkiler bölümü değerli, ama iş seçenekleri kısıtlı. Dış ticaret yolunu seçersen çok geniş fırsatlar açılıyor.
- Her paragraftan sonra aşağıdaki iç linklerden birini sırayla ekle.
- Anahtar kelimeyi paragraflar içine doğal yerleştir.
- Son paragraf güçlü bir harekete geçirici çağrı (CTA) olsun.

SABİT BANNER (yazının EN ÜSTÜNE, değiştirmeden ekle):
<div style="background: linear-gradient(135deg, #0d1b3e 0%, #1a3a6e 100%); padding: 24px 32px; border-radius: 10px; margin-bottom: 36px; text-align: center;">
  <p style="color: #e8b84b; font-size: 13px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; margin: 0 0 8px 0;">🎓 Özel Duyuru</p>
  <h3 style="color: #ffffff; font-size: 20px; font-weight: 800; margin: 0 0 14px 0; line-height: 1.4;">Uluslararası İlişkiler Öğrencisi / Mezunu musun?<br><span style="color: #e8b84b;">O Zaman Mutlaka Bu Projeyi İncele!</span></h3>
  <a href="https://www.kursdegilkariyer.online/uluslararasi-iliskiler-kariyer/" style="background: #e8b84b; color: #0d1b3e; padding: 12px 32px; border-radius: 6px; text-decoration: none; font-weight: 800; font-size: 15px; display: inline-block;">Projeyi İncele →</a>
</div>

İÇ LİNKLER (paragraf aralarına sırayla ekle):
LINK_1:
<div style="background:#f0f4ff; border-left: 4px solid #1a6bc8; padding: 16px 20px; border-radius: 6px; margin: 24px 0;">
  💡 <strong>Senin için önerilen program:</strong> <a href="https://www.kursdegilkariyer.online/uluslararasi-iliskiler-kariyer/" style="color:#1a6bc8; font-weight:700;">Uluslararası İlişkiler Kariyer Programı'na göz at →</a>
</div>

LINK_2:
<div style="background:#fff8e8; border-left: 4px solid #e8b84b; padding: 16px 20px; border-radius: 6px; margin: 24px 0;">
  🚀 <strong>İşe girmeden önce ödemiyorsun:</strong> <a href="https://www.kursdegilkariyer.online/ise-yerlestirme-programi/" style="color:#b8860b; font-weight:700;">İşe Yerleştirme Programı'nı incele →</a>
</div>

LINK_3:
<div style="background:#f0fff4; border-left: 4px solid #1a8a5a; padding: 16px 20px; border-radius: 6px; margin: 24px 0;">
  📞 <strong>Ücretsiz 3 saatlik deneme dersine katıl:</strong> <a href="https://www.kursdegilkariyer.online/ise-yerlestirme-programi/" style="color:#1a8a5a; font-weight:700;">Hemen başvur →</a>
</div>

DÖNDÜRME FORMATI — sadece geçerli JSON döndür, başka hiçbir şey yazma:
{
  "wp_baslik": "...",
  "meta_description": "...(max 155 karakter, SEO uyumlu)",
  "slug": "...(küçük harf, Türkçe karakter yok, tire ile ayrılmış)",
  "icerik_html": "...(tam HTML, banner dahil)"
}"""

    kullanici = f"Konu: {konu['baslik']}\nAna SEO kelimesi: {konu['seo']}"

    headers_api = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    body = {
        "model": "claude-opus-4-5",
        "max_tokens": 3000,
        "system": sistem,
        "messages": [{"role": "user", "content": kullanici}]
    }

    r = requests.post("https://api.anthropic.com/v1/messages", headers=headers_api, json=body)
    r.raise_for_status()

    metin = r.json()["content"][0]["text"].strip()

    # Markdown kod bloğu varsa temizle
    if "```" in metin:
        parcalar = metin.split("```")
        for parca in parcalar:
            parca = parca.strip()
            if parca.startswith("json"):
                parca = parca[4:].strip()
            try:
                return json.loads(parca)
            except:
                continue

    return json.loads(metin)


def wordpress_yayinla(yazi, seo_kelime):
    print(f"📤 WordPress'e yükleniyor...")

    kimlik = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()
    headers = {
        "Authorization": f"Basic {kimlik}",
        "Content-Type": "application/json"
    }

    veri = {
        "title":          yazi["wp_baslik"],
        "content":        yazi["icerik_html"],
        "status":         "publish",
        "slug":           yazi["slug"],
        "comment_status": "closed",
        "ping_status":    "closed",
        "meta": {
            "rank_math_title":         f"{yazi['wp_baslik']} | Kurs Değil Kariyer",
            "rank_math_description":   yazi["meta_description"],
            "rank_math_focus_keyword": seo_kelime,
        }
    }

    r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=headers, json=veri)

    if r.status_code == 201:
        data = r.json()
        print(f"✅ Yayınlandı!")
        print(f"🔗 URL: {data['link']}")
        return data
    else:
        print(f"❌ Hata: {r.status_code} — {r.text[:400]}")
        raise Exception(f"WordPress hatası: {r.status_code}")


def calistir():
    print(f"\n{'='*55}")
    print(f"🚀  Blog Ajanı — {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"{'='*55}")

    konu = bugunun_konusunu_sec()
    print(f"📌 Bugünkü konu: {konu['baslik']}")

    yazi = claude_ile_yazi_olustur(konu)
    wordpress_yayinla(yazi, konu["seo"])

    print(f"✅ Bitti! {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")


if __name__ == "__main__":
    calistir()
