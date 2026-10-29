@echo off
REM Botun yonetici oldugu kanali bulur ve .env dosyasina yazar.
cd /d "%~dp0"
.venv\Scripts\python -m bot.kanal_bul
pause
