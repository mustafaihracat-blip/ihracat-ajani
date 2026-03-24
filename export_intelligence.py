import anthropic
import json

# Yeni yapıda hem AI hem de Veri İşleme bir arada
client = anthropic.Anthropic(api_key="sk-ant-api03-0ew1GHEkJNEOhHP4YMuDoBWO-GteL284lcGQQFA29TV5c57znWjQm0PfPr-XFjKXCP65GifaLW9AnEXbDjJpA-Ldng6AAA")

def pazar_analizi_uret(hskodu, ulke):
    print(f"🚀 {ulke} pazarı için {hskodu} verileri analiz ediliyor...")
    
    prompt = f"""
    Sen bir kıdemli ihracat direktörüsün. 
    Ürün HS Kodu: {hskodu} (Elektrik Ekipmanları)
    Hedef Ülke: {ulke} (Nijerya)
    
    Lütfen Megates Enerji için:
    1. Bu pazara giriş stratejisi (3 madde).
    2. En kritik 5 rakip analizi.
    3. Yerel DISCO ve kamu kurumları için bir satış argümanı hazırla.
    """
    
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

if __name__ == "__main__":
    # 8504: Trafo ve statik konvertörler
    analiz = pazar_analizi_uret("8504", "Nijerya")
    print(analiz)
