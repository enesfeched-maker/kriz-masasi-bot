"""Paylaşımları Telegram kanalına gönderir."""

import html
import logging
import time

import requests

from bot.editor import Post

log = logging.getLogger(__name__)

CATEGORY_TAGS = {
    "savas": "#Savaş",
    "diplomasi": "#Diplomasi",
    "ekonomi": "#Ekonomi",
    "afet": "#Afet",
    "diger": "#Dünya",
}


def format_post(post: Post, channel: str) -> str:
    if not post.verified:
        label = "⚠️ <b>İDDİA</b>"
    elif post.breaking:
        label = "🔴 <b>SON DAKİKA</b>"
    else:
        label = "🌍"

    seen, links = set(), []
    for item in post.items:
        if item.source in seen:
            continue
        seen.add(item.source)
        links.append(f'<a href="{html.escape(item.link, quote=True)}">{html.escape(item.source)}</a>')

    lines = [
        f"{label} {html.escape(post.headline)}",
        "",
        html.escape(post.body),
        "",
        "🔗 " + " · ".join(links),
        f"{CATEGORY_TAGS.get(post.category, '#Dünya')} | {channel}",
    ]
    return "\n".join(lines)[:4000]


def send(token: str, chat_id: str, text: str) -> None:
    for attempt in range(3):
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "link_preview_options": {"is_disabled": True},
            },
            timeout=20,
        )
        if resp.status_code == 429:  # Telegram hız sınırı: bekleyip tekrar dene
            wait = resp.json().get("parameters", {}).get("retry_after", 5)
            time.sleep(wait + 1)
            continue
        if not resp.ok:
            raise RuntimeError(f"Telegram hatası {resp.status_code}: {resp.text}")
        return
    raise RuntimeError("Telegram hız sınırı aşılamadı")
