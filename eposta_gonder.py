import pandas as pd
import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date

# ========== AYARLAR ==========
SMTP_SERVER = "mail.kursdegilkariyer.online"
SMTP_PORT = 587
USERNAME = "bilgi@kursdegilkariyer.online"
PASSWORD = "Mustafa1234"
EXCEL_PATH = "/home/user/eposta_listesi.xlsx"
SABLON_PATH = "/home/user/eposta_sablon.html"
STATE_PATH = "/home/user/eposta_durum.json"
BASLANGIC_SAAT = 10
ARALIK_DK = 4

def durum_oku():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    return {"tarih": "", "index": 0}

def durum_kaydet(data):
    with open(STATE_PATH, "w") as f:
        json.dump(data, f)

bugun = str(date.today())
simdi = datetime.now()
gecen_dakika = (simdi.hour - BASLANGIC_SAAT) * 60 + simdi.minute
email_index = gecen_dakika // ARALIK_DK

df = pd.read_excel(EXCEL_PATH)
toplam = len(df)

durum = durum_oku()
if durum["tarih"] != bugun:
    durum = {"tarih": bugun, "index": 0}

if email_index >= toplam:
    print(f"✅ Bugün tüm {toplam} e-posta gönderildi.")
    exit()

if email_index < durum["index"]:
    print(f"⚠️ Bu e-posta zaten gönderildi (index: {email_index})")
    exit()

satir = df.iloc[email_index]
alici = satir["Alıcı E-posta"]

# HTML şablonu oku
with open(SABLON_PATH, "r", encoding="utf-8") as f:
    html = f.read()

html = html.replace("{{AD_SOYAD}}", "Yetkili")
html = html.replace("Sayın <strong>Yetkili</strong>", "Sayın Yetkili")

try:
    msg = MIMEMultipart("alternative")
    msg["From"] = f"Kurs Değil Kariyer <{USERNAME}>"
    msg["To"] = alici
    msg["Subject"] = "🎓 Dış Ticaret Eğitim Programı | Eğitim Al + İşe Yerleş + Sonra Öde"
    msg.attach(MIMEText("HTML destekleyen e-posta istemcisi kullanın.", "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
    server.ehlo()
    server.starttls()
    server.login(USERNAME, PASSWORD)
    server.sendmail(USERNAME, alici, msg.as_string())
    server.quit()

    durum["index"] = email_index + 1
    durum_kaydet(durum)
    print(f"✅ [{email_index+1}/{toplam}] → {alici} | {simdi.strftime('%H:%M')}")

except Exception as e:
    print(f"❌ Hata: {e}")
