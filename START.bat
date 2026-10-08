@echo off
start "Локальный Сервер Сайта" cmd /k "python -m http.server 8000"
start "Telegram Бот" cmd /k "python bot.py"
timeout /t 2 /nobreak >nul
start http://localhost:8000
