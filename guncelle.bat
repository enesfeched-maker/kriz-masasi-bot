@echo off
REM Botun en yeni surumunu GitHubdan indirir. .env ve kayitlar korunur.
cd /d "%~dp0"
powershell -NoProfile -Command "irm https://github.com/enesfeched-maker/kriz-masasi-bot/archive/refs/heads/main.zip -OutFile ..\bot.zip; Expand-Archive ..\bot.zip -DestinationPath .. -Force; Remove-Item ..\bot.zip"
echo Guncellendi. Botu baslatmak icin baslat.bat dosyasini calistir.
pause
