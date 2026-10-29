@echo off
REM Kriz Masasi botunu baslatir. Ilk calistirmada gerekli paketleri kurar.
REM Bot beklenmedik sekilde kapanirsa 30 saniye sonra kendini yeniden baslatir.
cd /d "%~dp0"
if not exist .venv (
    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
)
:basla
.venv\Scripts\python -m bot.main --loop
if %errorlevel%==2 (
    echo Ayar hatasi var, yukaridaki mesaja bak.
    pause
    exit /b 1
)
echo Bot kapandi, 30 saniye sonra yeniden baslatiliyor...
timeout /t 30 /nobreak >nul
goto basla
