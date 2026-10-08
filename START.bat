@echo off
start "Локальный Сервер Сайта" cmd /k "python -m http.server 8000"
start "Telegram Бот" cmd /k "python bot.py"
