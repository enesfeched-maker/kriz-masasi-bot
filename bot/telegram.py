"""Paylaşımları Telegram kanalına gönderir."""

import html
import logging
import time

import requests

from bot.editor import Post

log = logging.getLogger(__name__)

CAPTION_LIMIT = 1024


def format_post(post: Post, channel: str) -> str:
    """Kısa, kaynaksız kanal tarzı: "🔴 metin" ve altta kanal adı."""
    # "İddia" yalnızca çatışma ve diplomasi haberlerinde anlamlı;
    # tek kaynaklı piyasa verisi ya da afet haberi iddia sayılmaz.
    prefix = "🔴 "
    if not post.verified and post.category in ("savas", "diplomasi"):
        prefix += "<b>İddia:</b> "
    elif post.breaking:
        prefix += "<b>SON DAKİKA:</b> "

    footer = f"\n\n{channel}" if channel else ""
    body = html.escape(post.body, quote=False)

    # Fotoğraflı mesajlarda Telegram en fazla 1024 karakter kabul eder.
    room = CAPTION_LIMIT - len(prefix) - len(footer)
    if len(body) > room:
        body = body[:room].rsplit(" ", 1)[0] + "…"
    return prefix + body + footer


def _call(token: str, method: str, **kwargs) -> requests.Response:
    for attempt in range(3):
        resp = requests.post(f"https://api.telegram.org/bot{token}/{method}", timeout=60, **kwargs)
        if resp.status_code == 429:  # Telegram hız sınırı: bekleyip tekrar dene
            wait = resp.json().get("parameters", {}).get("retry_after", 5)
            time.sleep(wait + 1)
            continue
        return resp
    raise RuntimeError("Telegram hız sınırı aşılamadı")


def send(token: str, chat_id: str, text: str, image_url: str = "", silent: bool = False) -> None:
    """Paylaşımı gönderir. Fotoğraf varsa fotoğraflı, yoksa ya da gönderilemezse yalnız metin."""
    if image_url:
        # Önce Telegram fotoğrafı adresten kendisi çeksin; olmazsa indirip biz yükleyelim.
        resp = _call(token, "sendPhoto", json={
            "chat_id": chat_id, "photo": image_url, "caption": text, "parse_mode": "HTML",
            "disable_notification": silent})
        if resp.ok:
            return
        try:
            img = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            img.raise_for_status()
            resp = _call(token, "sendPhoto",
                         data={"chat_id": chat_id, "caption": text, "parse_mode": "HTML",
                               "disable_notification": str(silent).lower()},
                         files={"photo": ("foto.jpg", img.content)})
            if resp.ok:
                return
        except requests.RequestException:
            pass
        log.warning("Fotoğraf gönderilemedi, yalnız metin gidiyor: %s", image_url)

    resp = _call(token, "sendMessage", json={
        "chat_id": chat_id, "text": text, "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": True}, "disable_notification": silent})
    if not resp.ok:
        raise RuntimeError(f"Telegram hatası {resp.status_code}: {resp.text}")


MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
          "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
NUMBERS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]


def format_summary(items: list[str], day, channel: str) -> str:
    lines = [f"📋 <b>GÜNÜN ÖZETİ</b> | {day.day} {MONTHS[day.month - 1]} {day.year}", ""]
    for number, item in zip(NUMBERS, items):
        lines.append(f"{number} {html.escape(item, quote=False)}")
        lines.append("")
    lines.append("#GününÖzeti" + (f" | {channel}" if channel else ""))
    return "\n".join(lines)
