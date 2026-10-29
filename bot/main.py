"""Kriz Masası botu: kaynakları tara, yeni krizleri özetle, kanala gönder.

Kullanım:
  python -m bot.main          tek tur çalışır
  python -m bot.main --loop   bilgisayar açık kaldıkça her 10 dakikada bir tur atar

Ayarlar ortam değişkenlerinden ya da proje klasöründeki .env dosyasından okunur:
  TELEGRAM_BOT_TOKEN  BotFather'dan alınan anahtar
  TELEGRAM_CHANNEL    kanal adı, örn. @krizmasasi
  OLLAMA_MODEL        (isteğe bağlı) varsayılan gemma3:12b
  OLLAMA_URL          (isteğe bağlı) varsayılan http://localhost:11434
  MAX_POSTS_PER_RUN   (isteğe bağlı) bir turda en fazla paylaşım, varsayılan 4
  INTERVAL_MINUTES    (isteğe bağlı) --loop modunda turlar arası süre, varsayılan 10
  DRY_RUN=1           kanala göndermek yerine paylaşımları ekrana yazar
"""

import json
import logging
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
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"'))


def run_once() -> None:
    dry_run = os.environ.get("DRY_RUN") == "1"
    channel = os.environ.get("TELEGRAM_CHANNEL", "@krizmasasi")
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

    posts = []
    if new_items_to_post:
        posts = editor.write_posts(new_items_to_post, [r["h"] for r in recent], max_posts)

    for post in posts:
        text = telegram.format_post(post, channel)
        image = next((i.image for i in post.items if i.image), "")
        if not image:
            image = next((img for i in post.items if (img := feeds.page_image(i.link))), "")
        if dry_run:
            print("-" * 40 + f"\n[Fotoğraf: {image or 'yok'}]\n" + text)
        else:
            telegram.send(os.environ["TELEGRAM_BOT_TOKEN"], channel, text, image)
            time.sleep(3)
        recent.append({"t": now, "h": post.headline})

    for item in new_items:
        seen[item.id] = now
    if not dry_run:
        save_state({"seen": seen, "recent": recent, "failed_sources": failed})
    log.info("Tur bitti: %d paylaşım.", len(posts))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M")
    load_env_file()
    if "--loop" not in sys.argv:
        run_once()
        return 0

    interval = float(os.environ.get("INTERVAL_MINUTES", "10")) * 60
    while True:
        try:
            run_once()
        except Exception:  # internet ya da model geçici olarak çökerse bot durmasın
            log.exception("Tur hata verdi, bir sonraki turda tekrar denenecek")
        time.sleep(interval)


if __name__ == "__main__":
    sys.exit(main())
