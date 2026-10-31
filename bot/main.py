"""Kriz Masası botu: kaynakları tara, yeni krizleri özetle, kanala gönder.

Kullanım:
  python -m bot.main          tek tur çalışır
  python -m bot.main --loop   bilgisayar açık kaldıkça her 10 dakikada bir tur atar
  python -m bot.tray          aynısını pencere açmadan, saat yanındaki K simgesiyle yapar

Ayarlar ortam değişkenlerinden ya da proje klasöründeki .env dosyasından okunur:
  TELEGRAM_BOT_TOKEN  BotFather'dan alınan anahtar
  TELEGRAM_CHANNEL    kanal adı (örn. @krizmasasitr) ya da sayısal kimliği; kanal_bul.bat ayarlar
  SIGNATURE           (isteğe bağlı) paylaşımların altına yazılacak imza (örn. @krizmasasitr), varsayılan boş
  OLLAMA_MODEL        (isteğe bağlı) varsayılan gemma3:4b
  OLLAMA_URL          (isteğe bağlı) varsayılan http://localhost:11434
  OLLAMA_KEEP_ALIVE   (isteğe bağlı) model turdan sonra ne kadar bellekte kalsın, varsayılan 1m
  MAX_POSTS_PER_RUN   (isteğe bağlı) bir turda en fazla paylaşım, varsayılan 4
  INTERVAL_MINUTES    (isteğe bağlı) --loop modunda turlar arası süre, varsayılan 10
  QUIET_HOURS         (isteğe bağlı) bildirimsiz paylaşım saatleri, varsayılan 0-8; kapatmak için boş bırak
  DAILY_MAX_POSTS     (isteğe bağlı) günde en fazla paylaşım, varsayılan 40
  HOURLY_MAX_POSTS    (isteğe bağlı) saatte en fazla paylaşım, varsayılan 3
  SUMMARY_HOUR        (isteğe bağlı) günün özetinin gideceği saat, varsayılan 21; kapatmak için boş bırak
  DRY_RUN=1           kanala göndermek yerine paylaşımları ekrana yazar
"""

import datetime
import json
import logging
import logging.handlers
import os
import sys
import time

from bot import editor, feeds, telegram

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_PATH = os.path.join(ROOT, "sources.yaml")
STATE_PATH = os.path.join(ROOT, "state", "state.json")

MAX_AGE_HOURS = 6         # bundan eski haberlere bakma
SEEN_TTL = 7 * 24 * 3600  # görülen haber kimliklerini bu kadar sakla
RECENT_TTL = 48 * 3600    # son paylaşımları tekrar önlemek için bu kadar sakla
MAX_ITEMS_PER_RUN = 30    # modele bir turda verilecek en fazla haber

log = logging.getLogger("krizmasasi")


def load_state() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1, sort_keys=True)


def load_env_file() -> None:
    """Proje klasöründeki .env dosyasını okur (KEY=değer satırları)."""
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    # PowerShell .env dosyasını farklı bir kodlamayla kaydetmiş olabilir; okunamayan harfleri atla.
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"'))


def is_quiet_now() -> bool:
    """Gece saatlerinde paylaşımlar bildirim sesi çıkarmadan gider."""
    hours = os.environ.get("QUIET_HOURS", "0-8").strip()
    if not hours:
        return False
    start, end = (int(h) for h in hours.split("-"))
    hour = datetime.datetime.now().hour
    return start <= hour < end if start <= end else hour >= start or hour < end


def start_of_today() -> float:
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return today.timestamp()


def post_budget(recent: list[dict], now: float) -> int:
    """Günlük ve saatlik sınırlara göre bu turda en fazla kaç paylaşım yapılabileceği."""
    daily = int(os.environ.get("DAILY_MAX_POSTS", "40"))
    hourly = int(os.environ.get("HOURLY_MAX_POSTS", "3"))
    today = sum(1 for r in recent if r["t"] >= start_of_today())
    last_hour = sum(1 for r in recent if now - r["t"] < 3600)
    return max(0, min(daily - today, hourly - last_hour))


def maybe_send_summary(state: dict, handle: str, channel: str, dry_run: bool) -> None:
    """Belirlenen saatten sonra, o gün henüz gönderilmediyse günün özetini paylaşır."""
    hour = os.environ.get("SUMMARY_HOUR", "21").strip()
    now = datetime.datetime.now()
    if not hour or now.hour < int(hour) or state.get("summary_date") == now.date().isoformat():
        return
    today = [r for r in state.get("recent", []) if r["t"] >= start_of_today()]
    if len(today) < 3:
        return  # özetlenecek kadar haber yok
    items = editor.write_daily_summary(today)
    if not items:
        return
    text = telegram.format_summary(items, now.date(), handle)
    if dry_run:
        print("-" * 40 + "\n" + text)
    else:
        telegram.send(os.environ["TELEGRAM_BOT_TOKEN"], channel, text, silent=is_quiet_now())
    state["summary_date"] = now.date().isoformat()
    log.info("Günün özeti paylaşıldı (%d madde).", len(items))


def pick_media(post) -> tuple[str, str]:
    """Paylaşıma konacak (video, fotoğraf) adreslerini seçer. Önce modelin seçtiği asıl
    haberin görseline bakar; model görselin başka bir olaya ait olduğunu söylerse atlar."""
    for n, item in enumerate(post.items):
        image = item.image or feeds.page_image(item.link)
        if not (item.video or image):
            continue
        match = editor.same_event(post, item)
        # Kontrol yapılamadıysa yalnızca asıl haberin görseline güven.
        if match or (match is None and n == 0):
            return item.video, image
        log.info("Görsel paylaşımla uyuşmadı, kullanılmadı: %s | %s", post.headline, item.title[:80])
    log.info("Görselsiz paylaşım: %s", post.headline)
    return "", ""


def run_once() -> None:
    dry_run = os.environ.get("DRY_RUN") == "1"
    channel = os.environ.get("TELEGRAM_CHANNEL", "@krizmasasitr")
    # Paylaşımların altına kanal adı yazılmaz; istenirse .env'de SIGNATURE ile açılır.
    handle = os.environ.get("SIGNATURE", "")
    max_posts = int(os.environ.get("MAX_POSTS_PER_RUN", "4"))

    now = time.time()
    state = load_state()
    first_run = "seen" not in state
    seen = {k: v for k, v in state.get("seen", {}).items() if now - v < SEEN_TTL}
    recent = [r for r in state.get("recent", []) if now - r["t"] < RECENT_TTL]

    items, failed = feeds.fetch_all(feeds.load_sources(SOURCES_PATH), MAX_AGE_HOURS)
    new_items = [i for i in items if i.id not in seen]
    log.info("%d haber okundu, %d yeni. Çalışmayan kaynaklar: %s",
             len(items), len(new_items), ", ".join(failed) or "yok")

    if first_run and not dry_run:
        # İlk turda eski haberleri kanala yığmamak için hepsini görüldü say.
        log.info("İlk çalıştırma: mevcut haberler görüldü olarak işaretlendi, paylaşım yapılmadı.")
        new_items_to_post = []
    else:
        new_items_to_post = new_items[:MAX_ITEMS_PER_RUN]

    budget = min(max_posts, post_budget(recent, now))
    if new_items_to_post and budget == 0:
        log.info("Paylaşım sınırına ulaşıldı (günde %s, saatte %s), bu tur paylaşım yok.",
                 os.environ.get("DAILY_MAX_POSTS", "40"), os.environ.get("HOURLY_MAX_POSTS", "3"))

    posts = []
    if new_items_to_post and budget:
        posts = editor.write_posts(new_items_to_post, [r["h"] for r in recent], budget)

    silent = is_quiet_now()
    sent = 0
    for post in posts:
        text = telegram.format_post(post, handle)
        video, image = pick_media(post)
        if dry_run:
            print("-" * 40 + f"\n[Video: {video or 'yok'}] [Fotoğraf: {image or 'yok'}]\n" + text)
        else:
            try:
                telegram.send(os.environ["TELEGRAM_BOT_TOKEN"], channel, text, image, silent, video)
            except Exception as exc:  # bir paylaşım gitmezse diğerleri yine gitsin
                log.error("Paylaşım gönderilemedi: %s", exc)
                continue
            time.sleep(3)
        sent += 1
        recent.append({"t": now, "h": post.headline, "b": post.body[:300]})

    if posts and not sent and not dry_run:
        # Hiçbiri gitmediyse haberleri görüldü sayma, bir sonraki turda yeniden denensin.
        raise RuntimeError("Hiçbir paylaşım gönderilemedi. Kanal adını ve botun yönetici iznini kontrol et.")

    for item in new_items:
        seen[item.id] = now
    state.update({"seen": seen, "recent": recent, "failed_sources": failed})
    if not dry_run:
        save_state(state)
    log.info("Tur bitti: %d paylaşım%s.", sent, " (gece modu, bildirimsiz)" if silent and sent else "")

    try:
        maybe_send_summary(state, handle, channel, dry_run)
        if not dry_run:
            save_state(state)
    except Exception:  # özet gitmezse bir sonraki turda yeniden denenir
        log.exception("Günün özeti gönderilemedi")


def setup() -> int:
    """Kayıtları ve ayarları hazırlar. Sorun yoksa 0, ayar hatası varsa 2 döner."""
    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    file_log = logging.handlers.RotatingFileHandler(
        os.path.join(ROOT, "logs", "bot.log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_log.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M"))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M")
    logging.getLogger().addHandler(file_log)
    load_env_file()
    if os.environ.get("DRY_RUN") != "1" and not os.environ.get("TELEGRAM_BOT_TOKEN"):
        log.error(".env dosyasında TELEGRAM_BOT_TOKEN yok. Anahtarı ekleyip botu yeniden başlat.")
        return 2
    return 0


def loop(on_status=None, stop=None) -> None:
    """Her INTERVAL_MINUTES dakikada bir tur atar. on_status(ok, mesaj) her turdan sonra çağrılır."""
    interval = float(os.environ.get("INTERVAL_MINUTES", "10")) * 60
    while not (stop and stop.is_set()):
        try:
            run_once()
            if on_status:
                on_status(True, "Son tur " + datetime.datetime.now().strftime("%H:%M") + " başarılı")
        except Exception as exc:  # internet ya da model geçici olarak çökerse bot durmasın
            log.exception("Tur hata verdi, bir sonraki turda tekrar denenecek")
            if on_status:
                on_status(False, f"Hata: {exc}"[:120])
        if stop:
            stop.wait(interval)
        else:
            time.sleep(interval)


def main() -> int:
    if code := setup():
        return code  # baslat.bat 2 kodunu görünce yeniden denemez, durur
    if "--loop" not in sys.argv:
        run_once()
        return 0
    loop()


if __name__ == "__main__":
    sys.exit(main())
