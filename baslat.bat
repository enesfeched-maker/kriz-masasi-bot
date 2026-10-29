@echo off
REM Kriz Masasi botunu baslatir. Ilk calistirmada gerekli paketleri kurar.
cd /d "%~dp0"
if not exist .venv (
    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
)
.venv\Scripts\python -m bot.main --loop
pause
