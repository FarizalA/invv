@echo off
title Telegram Bot - Invoice Pemasukan Otomatis
cd /d "%~dp0"

echo ========================================================
echo   Telegram Bot Auto Pemasukan (Sheets, Drive & Gemini)
echo ========================================================
echo.

python telegram_bot.py

pause
