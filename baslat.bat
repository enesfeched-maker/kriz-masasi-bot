@echo off
REM Kriz Masasi botunu arka planda baslatir.
REM Gerekli paketleri kurar ya da gunceller, sonra bu pencere kapanir.
cd /d "%~dp0"
if not exist .venv python -m venv .venv
.venv\Scripts\python -m pip install -q -r requirements.txt
REM Bot, Botlar panelinin KrizMasasi goreviyle yonetiliyorsa onu (yeniden) baslat; iki kopya calismasin.
schtasks /Query /TN KrizMasasi >nul 2>&1
if %errorlevel%==0 (
    schtasks /End /TN KrizMasasi >nul 2>&1
    schtasks /Run /TN KrizMasasi >nul
    exit /b
)
start "" .venv\Scripts\pythonw.exe -m bot.tray
