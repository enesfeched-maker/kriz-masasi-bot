# Kriz Masası botu

Dünyadaki krizleri (savaş, diplomasi, ekonomik şoklar, afetler) güvenilir kaynaklardan
toplayıp Türkçe özetleyen ve [@krizmasasi](https://t.me/krizmasasi) Telegram kanalına
gönderen bot. Özetleri bilgisayarında çalışan ücretsiz bir yapay zekâ modeli
([Ollama](https://ollama.com)) yazar, hiçbir ücretli servis kullanılmaz.

## Nasıl çalışır

Bot bilgisayarın açık kaldıkça her 10 dakikada bir tur atar. Her turda:

1. `sources.yaml` içindeki haber kaynaklarını okur ve son 6 saatin yeni haberlerini alır.
2. Yeni haberleri yerel modele verir. Model konu dışı haberleri eler, aynı olayı anlatan
   haberleri birleştirir, son 48 saatte paylaşılmış olayları tekrarlamaz ve en önemli
   birkaç olay için kısa Türkçe paylaşımlar yazar.
3. Paylaşımları haberin fotoğrafıyla (varsa) ve kaynak adıyla kanala gönderir:
   - 🔴 **SON DAKİKA**: birinci grup bir kaynaktan ya da iki farklı kaynaktan gelen acil haber
   - 🌍 doğrulanmış diğer haberler
   - ⚠️ **İDDİA**: tek bir ikinci grup kaynağa dayanan haber
4. Görülen haberleri `state/state.json` dosyasına kaydeder ki aynı haber iki kez gitmesin.

İlk turda eski haberleri kanala yığmamak için hiçbir şey paylaşmaz, yalnızca mevcut
haberleri görüldü olarak işaretler. Paylaşımlar ikinci turdan itibaren başlar.

## Kurulum (Windows)

1. **Python:** [python.org](https://www.python.org/downloads/) üzerinden Python 3.12'yi kur.
   Kurulumda **"Add python.exe to PATH"** kutusunu işaretle.
2. **Ollama:** [ollama.com/download](https://ollama.com/download) üzerinden Ollama'yı kur.
   Sonra bir komut penceresi (cmd) aç ve modeli indir:
   ```
   ollama pull gemma3:12b
   ```
3. **Bot dosyaları:** Bu sayfada yeşil **Code** düğmesi → **Download ZIP** ile indir ve bir
   klasöre çıkar (örn. `C:\kriz-masasi-bot`).
4. **Ayarlar:** Klasördeki `.env.example` dosyasının bir kopyasını `.env` adıyla oluştur,
   Not Defteri ile aç ve BotFather'ın verdiği anahtarı `TELEGRAM_BOT_TOKEN=` satırına yaz.
5. **Kanal:** Botu kanala **yönetici** olarak ekle ve "Mesaj gönderme" iznini ver.
6. **Başlat:** `baslat.bat` dosyasına çift tıkla. İlk açılışta gerekli paketleri kurar,
   sonra çalışmaya başlar. Pencere açık kaldıkça bot çalışır.

**Bilgisayar açıldığında kendiliğinden başlasın istersen:** `Win + R` → `shell:startup`
yaz → açılan klasöre `baslat.bat` için bir kısayol koy.

## Model seçimi

Model ne kadar büyükse Türkçesi ve haber seçimi o kadar iyi olur ama bilgisayarı daha
çok yorar. `.env` dosyasındaki `OLLAMA_MODEL` satırından değiştirilir.

| Bilgisayar | Önerilen model |
|---|---|
| 6 GB ya da daha fazla ekran kartı belleği (VRAM), 16 GB RAM | `gemma3:12b` (varsayılan). 6-8 GB VRAM'de model kısmen işlemcide çalışır, bir tur birkaç dakika sürer. 10 dakikalık aralık için yeterli. |
| Ekran kartı zayıf ya da yok | `gemma3:4b` (daha hızlı, Türkçesi biraz daha zayıf) |
| 16 GB ya da daha fazla VRAM | `gemma3:27b` |

Modeli değiştirdiysen önce `ollama pull <model adı>` ile indirmeyi unutma.

## Ayarlar

- **Kaynak eklemek ya da çıkarmak:** `sources.yaml` dosyasını düzenle.
- **`.env` içindeki diğer ayarlar:** `MAX_POSTS_PER_RUN` (bir turda en fazla paylaşım,
  varsayılan 4), `INTERVAL_MINUTES` (turlar arası dakika, varsayılan 10).
- **Çalışmayan kaynaklar:** Pencerede her turda listelenir, ayrıca `state/state.json`
  içindeki `failed_sources` alanına yazılır.
- **Deneme:** `.env` dosyasına `DRY_RUN=1` eklersen bot kanala göndermez, paylaşımları
  yalnızca pencereye yazar.
