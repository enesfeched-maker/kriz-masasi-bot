"""Kriz Masası botu: kaynakları tara, yeni krizleri özetle, kanala gönder.

Her çalıştırmada bir tur yapar. GitHub Actions bunu birkaç dakikada bir çalıştırır.

Ortam değişkenleri:
  TELEGRAM_BOT_TOKEN  BotFather'dan alınan anahtar
  TELEGRAM_CHANNEL    kanal adı, örn. @krizmasasi
  ANTHROPIC_API_KEY   Claude API anahtarı
  CLAUDE_MODEL        (isteğe bağlı) varsayılan claude-opus-5-5
  MAX_POSTS_PER_RUN   (isteğe bağlı) bir turda en fazla paylaşım, varsayılan 4
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
MAX_ITEMS_PER_RUN = 80    # Claude'a bir turda verilecek en fazla haber

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


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
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

    if first_run:
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
        if dry_run:
            print("-" * 40 + "\n" + text)
        else:
            telegram.send(os.environ["TELEGRAM_BOT_TOKEN"], channel, text)
            time.sleep(3)
        recent.append({"t": now, "h": post.headline})

    for item in new_items:
        seen[item.id] = now
    if not dry_run:
        save_state({"seen": seen, "recent": recent, "failed_sources": failed})
    log.info("Tur bitti: %d paylaşım.", len(posts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
