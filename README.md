# Kriz Masası botu

Dünyadaki krizleri (savaş, diplomasi, ekonomik şoklar, afetler) güvenilir kaynaklardan
toplayıp Türkçe özetleyen ve [@krizmasasi](https://t.me/krizmasasi) Telegram kanalına
gönderen bot.

## Nasıl çalışır

GitHub Actions botu her 10 dakikada bir çalıştırır. Her turda bot:

1. `sources.yaml` içindeki haber kaynaklarını okur ve son 6 saatin yeni haberlerini alır.
2. Yeni haberleri Claude'a verir. Claude konu dışı haberleri eler, aynı olayı anlatan
   haberleri birleştirir, son 48 saatte paylaşılmış olayları tekrarlamaz ve en önemli
   birkaç olay için kısa Türkçe paylaşımlar yazar.
3. Paylaşımları kaynak linkleriyle kanala gönderir:
   - 🔴 **SON DAKİKA**: birinci grup bir kaynaktan ya da iki farklı kaynaktan gelen acil haber
   - 🌍 doğrulanmış diğer haberler
   - ⚠️ **İDDİA**: tek bir ikinci grup kaynağa dayanan haber
4. Görülen haberleri `state/state.json` dosyasına kaydeder ki aynı haber iki kez gitmesin.

İlk çalıştırmada eski haberleri kanala yığmamak için hiçbir şey paylaşmaz, yalnızca
mevcut haberleri görüldü olarak işaretler.

## Kurulum

1. **Telegram botu:** Telegram'da [@BotFather](https://t.me/BotFather)'a `/newbot` yaz,
   bir isim ver ve sana verdiği anahtarı (token) kaydet.
2. **Kanal:** Kanalını aç, botu kanala **yönetici** olarak ekle ve "Mesaj gönderme" iznini ver.
3. **Claude API anahtarı:** [platform.claude.com](https://platform.claude.com) üzerinden bir API
   anahtarı oluştur ve hesabına bakiye yükle.
4. **GitHub anahtarları:** Bu depoda *Settings → Secrets and variables → Actions* bölümüne git.
   - *Secrets* sekmesine `TELEGRAM_BOT_TOKEN` ve `ANTHROPIC_API_KEY` ekle.
   - Kanal adın `@krizmasasi` değilse *Variables* sekmesine `TELEGRAM_CHANNEL` ekle (örn. `@krizmasasi_tr`).
   - Farklı bir Claude modeli kullanmak istersen *Variables* sekmesine `CLAUDE_MODEL` ekle.
5. **Başlat:** *Actions* sekmesinde "Kriz Masası botu" iş akışını aç ve **Run workflow** ile
   bir kez elle çalıştır. Sonrasında kendiliğinden her 10 dakikada bir çalışır.

## Ayarlar

- **Kaynak eklemek ya da çıkarmak:** `sources.yaml` dosyasını düzenle.
- **Bir turda en fazla paylaşım:** `MAX_POSTS_PER_RUN` değişkeni (varsayılan 4).
- **Çalışmayan kaynaklar:** Her turun kaydında ve `state/state.json` içindeki
  `failed_sources` alanında listelenir.

## Yerelde deneme

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
DRY_RUN=1 python -m bot.main
```

`DRY_RUN=1` paylaşımları kanala göndermek yerine ekrana yazar ve durumu kaydetmez.
İlk çalıştırma hiçbir şey paylaşmadığı için yerelde denerken önce bir kez `DRY_RUN`
olmadan, `TELEGRAM_BOT_TOKEN` vermeden çalıştırmak yerine `state/state.json` dosyasına
`{"seen": {}}` yazabilirsin.
