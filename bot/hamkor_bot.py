"""
Hamkor Top — Telegram Bot + Mini App Server
MVP версия: бот запускает Mini App интерфейс для свайп-матчинга
"""

import asyncio
import json
import os
import http.server
import socketserver
import threading
from pathlib import Path

# ---- КОНФИГУРАЦИЯ ----
BOT_TOKEN = "8877540443:AAEMfWYjusdNCaMMvQBVOJ_QHwaDoPOWSwY"
WEBAPP_DIR = Path(__file__).parent.parent / "webapp"
PORT = 8080

# ---- Mini App HTTP-сервер (обслуживает index.html) ----
class HamkorHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEBAPP_DIR), **kwargs)
    
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()
    
    def log_message(self, format, *args):
        pass  # тихий режим

def start_web_server():
    """Запускает HTTP-сервер для раздачи Mini App"""
    with socketserver.TCPServer(("", PORT), HamkorHandler) as httpd:
        print(f"🌐 Mini App доступен: http://localhost:{PORT}")
        httpd.serve_forever()

# ---- Telegram Bot (aiogram 3) ----
try:
    from aiogram import Bot, Dispatcher, types
    from aiogram.filters import Command
    from aiogram.types import (
        InlineKeyboardMarkup, InlineKeyboardButton,
        WebAppInfo, MenuButtonWebApp
    )
    AIOGRAM_AVAILABLE = True
except ImportError:
    AIOGRAM_AVAILABLE = False
    print("⚠️ aiogram не установлен. Установи: pip install aiogram")

# --- ВРЕМЕННАЯ ЗАГЛУШКА (пока нет публичного URL) ---
# Для реальной работы Mini App в Telegram нужен HTTPS URL.
# Варианты быстрого развёртывания:
# 1. ngrok (локальный туннель) — временно для теста
# 2. PythonAnywhere (бесплатный хостинг Python)
# 3. Railway / Render (бесплатный tier)
# 
# Пока используем локальный URL — бот будет работать,
# Mini App откроется в браузере.

# Заглушка: позже заменить на реальный URL
WEBAPP_URL = f"http://localhost:{PORT}"

async def on_start(message: types.Message):
    """Обработчик /start"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Открыть Hamkor Top",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )],
        [InlineKeyboardButton(
            text="📋 Что это?",
            callback_data="about"
        )]
    ])
    
    await message.answer(
        "🤝 <b>Hamkor Top</b> — твой AI-партнёр для карьеры!\n\n"
        "Свайпай вакансии как в Тиндере. "
        "Находи работу, сотрудников и нетворкинг.\n\n"
        "Создано в Узбекистане 🇺🇿",
        reply_markup=kb,
        parse_mode="HTML"
    )

async def on_about(callback: types.CallbackQuery):
    """Обработчик кнопки 'Что это?'"""
    await callback.message.answer(
        "🎯 <b>Как это работает:</b>\n\n"
        "1. Заполни профиль за 2 минуты\n"
        "2. Свайпай карточки вакансий/специалистов\n"
        "3. 👍 Вправо — интересно\n"
        "4. 👎 Влево — не подходит\n"
        "5. Обоюдный лайк = Матч! 🎉\n\n"
        "<b>Геймификация:</b>\n"
        "• XP за каждое действие\n"
        "• Уровни от Yangi до Hamkor\n"
        "• Ежедневное комбо (x2 буст)\n"
        "• Бейджи и достижения\n",
        parse_mode="HTML"
    )
    await callback.answer()

async def main():
    """Запуск Telegram-бота"""
    if not AIOGRAM_AVAILABLE:
        print("❌ aiogram не найден. Установка...")
        os.system("pip install aiogram")
        return
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрируем обработчики
    dp.message.register(on_start, Command("start"))
    dp.callback_query.register(on_about, lambda c: c.data == "about")
    
    # Устанавливаем кнопку меню (Mini App в боковом меню Telegram)
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🚀 Hamkor Top",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        )
        print("✅ Кнопка меню установлена")
    except Exception as e:
        print(f"⚠️ Не удалось установить кнопку меню: {e}")
    
    print("🤖 Бот @hamkor_top_bot запущен!")
    await dp.start_polling(bot)

# ---- ГЛАВНЫЙ ЗАПУСК ----
if __name__ == "__main__":
    print("=" * 50)
    print("🤝 HAMKOR TOP — AI Career Platform")
    print("=" * 50)
    
    # Запускаем HTTP-сервер в отдельном потоке
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    
    # Запускаем бота
    asyncio.run(main())
