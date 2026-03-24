import anthropic

# Buraya Anthropic API Key'ini yapıştır
# Görselinde siyahla kapatılan o uzun kodu tırnak içine koy
client = anthropic.Anthropic(api_key="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")

def instagram_ajani(konu):
    print(f"\n🚀 '{konu}' konusu üzerine çalışıyorum...")
    
    prompt = f"""
    Sen bir kıdemli uluslararası ticaret uzmanısın ve 'İhracat Fabrikası' markasının içerik üreticisisin.
    Konu: {konu}
    
    Lütfen şunları hazırla:
    1. Dikkat çekici bir Instagram Reels/Post başlığı.
    2. Bilgi verici, profesyonel ama akıcı bir açıklama metni.
    3. En az 10 adet popüler ve sektörel hashtag.
    4. Bu post için yapay zekaya (DALL-E veya Midjourney) verilecek İngilizce görsel oluşturma komutu (image prompt).
    """
    
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Yanıtı ekrana yazdır
    print("\n--- HAZIRLANAN İÇERİK ---")
    print(message.content[0].text)

# ÇALIŞTIRMA: Buraya istediğin gündemi yazabilirsin
if __name__ == "__main__":
    instagram_ajani("İran-İsrail geriliminin Orta Doğu ihracat hatlarına etkisi")
