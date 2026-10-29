"""Botu pencere açmadan çalıştırır ve saatin yanında bir K simgesi gösterir.

Yeşil K: bot çalışıyor, son tur başarılı.  Kırmızı K: son turda hata var.
Simgeye sağ tıklayınca durumu görebilir, kayıtları açabilir ya da botu kapatabilirsin.
"""

import os
import socket
import sys
import threading

import pystray
from PIL import Image, ImageDraw, ImageFont

from bot import main

GREEN = (34, 160, 70)
RED = (210, 40, 40)
GREY = (120, 120, 120)
LOCK_PORT = 47291  # aynı anda iki bot çalışmasın diye tutulan yerel port


def make_icon(color: tuple) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, 63, 63), fill=color)
    try:
        font = ImageFont.truetype("arialbd.ttf", 42)
    except OSError:
        font = ImageFont.load_default(size=42)
    draw.text((32, 33), "K", fill="white", font=font, anchor="mm")
    return img


def run() -> int:
    lock = socket.socket()
    try:
        lock.bind(("127.0.0.1", LOCK_PORT))
    except OSError:
        return 0  # bot zaten çalışıyor

    status = {"text": "Başlıyor..."}
    stop = threading.Event()

    def open_logs(icon, item):
        os.startfile(os.path.join(main.ROOT, "logs", "bot.log"))

    def quit_bot(icon, item):
        stop.set()
        icon.stop()

    icon = pystray.Icon(
        "kriz-masasi",
        make_icon(GREY),
        "Kriz Masası botu: başlıyor",
        menu=pystray.Menu(
            pystray.MenuItem(lambda item: status["text"], None, enabled=False),
            pystray.MenuItem("Kayıtları aç", open_logs),
            pystray.MenuItem("Botu kapat", quit_bot),
        ),
    )

    def on_status(ok: bool, text: str) -> None:
        status["text"] = text
        icon.icon = make_icon(GREEN if ok else RED)
        icon.title = ("Kriz Masası botu: " + text)[:120]
        try:
            icon.update_menu()
        except Exception:  # simge henüz ekranda değilse menü bir sonraki açılışta güncellenir
            pass

    if main.setup():
        on_status(False, ".env dosyasında TELEGRAM_BOT_TOKEN yok")
    else:
        threading.Thread(target=main.loop, args=(on_status, stop), daemon=True).start()
    icon.run()
    return 0


if __name__ == "__main__":
    sys.exit(run())
