@echo off
REM Botu pencereli calistirir; hata ararken ise yarar. Normal kullanim icin baslat.bat.
cd /d "%~dp0"
.venv\Scripts\python -m bot.main --loop
pause
