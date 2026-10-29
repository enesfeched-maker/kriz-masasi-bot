@echo off
REM Kriz Masasi botunu arka planda baslatir. Saat yanindaki K simgesinden takip edilir.
REM Gerekli paketleri kurar ya da gunceller, sonra bu pencere kapanir.
cd /d "%~dp0"
if not exist .venv python -m venv .venv
.venv\Scripts\python -m pip install -q -r requirements.txt
start "" .venv\Scripts\pythonw.exe -m bot.tray
