"""Botun yönetici olduğu kanalı bulur ve .env dosyasına yazar.

Kullanım: python -m bot.kanal_bul   (ya da kanal_bul.bat)

Kanal adı (@...) ile bulunamayan kanallarda, örneğin gizli kanallarda, Telegram'ın
verdiği sayısal kimliği (-100...) kullanmak gerekir. Bu araç o kimliği botun son
güncellemelerinden okur.
"""

import os
import re
import sys

import requests

from bot.main import ROOT, load_env_file

ENV_PATH = os.path.join(ROOT, ".env")


def api(token: str, method: str, **params) -> dict:
    resp = requests.get(f"https://api.telegram.org/bot{token}/{method}", params=params, timeout=30)
    return resp.json()


def find_channels(token: str) -> dict:
    """Botun eklendiği ya da kanalda mesaj gördüğü kanalları döner: {id: chat}."""
    channels = {}
    for update in api(token, "getUpdates").get("result", []):
        for key in ("my_chat_member", "channel_post", "edited_channel_post"):
            chat = update.get(key, {}).get("chat", {})
            if chat.get("type") == "channel":
                channels[chat["id"]] = chat
    return channels


def set_env(values: dict) -> None:
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    for key, value in values.items():
        pattern = re.compile(rf"^\s*{key}\s*=")
        lines = [line for line in lines if not pattern.match(line)]
        lines.append(f"{key}={value}")
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    load_env_file()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    me = api(token, "getMe") if token else {}
    if not me.get("ok"):
        print("HATA: .env dosyasındaki TELEGRAM_BOT_TOKEN geçersiz ya da eksik.")
        return 1
    bot_id = me["result"]["id"]
    print(f"Bot: @{me['result']['username']}")

    channels = find_channels(token)
    if not channels:
        print("\nBotun eklendiği bir kanal bulunamadı. Şunları yap ve bu aracı yeniden çalıştır:")
        print("  1. Botu kanala yönetici olarak ekle (zaten ekliysen çıkarıp yeniden ekle).")
        print("  2. Kanala herhangi bir mesaj yaz, örneğin 'test'.")
        return 1

    usable = []
    for chat_id, chat in channels.items():
        member = api(token, "getChatMember", chat_id=chat_id, user_id=bot_id).get("result", {})
        can_post = member.get("status") == "administrator" and member.get("can_post_messages", False)
        handle = f"@{chat['username']}" if chat.get("username") else "(gizli kanal)"
        print(f"Kanal: {chat.get('title')}  {handle}  kimlik: {chat_id}  "
              f"{'mesaj gönderebilir' if can_post else 'YÖNETİCİ DEĞİL ya da mesaj izni yok'}")
        if can_post:
            usable.append(chat)

    if not usable:
        print("\nBot kanalda yönetici değil ya da 'Mesaj gönder' izni kapalı. Bunu düzeltip yeniden çalıştır.")
        return 1

    chat = usable[0]
    handle = f"@{chat['username']}" if chat.get("username") else ""
    set_env({"TELEGRAM_CHANNEL": chat["id"], "CHANNEL_HANDLE": handle})
    print(f"\nTAMAM: .env dosyasına '{chat.get('title')}' kanalı yazıldı. Botu yeniden başlat.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
