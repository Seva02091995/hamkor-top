"""
Hamkor Top — Telegram Bot + Mini App Server
Принимает данные из Mini App, сохраняет профили, пересылает B2B-заявки.
"""
import asyncio, json, os, logging, base64, urllib.parse
from pathlib import Path

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8877540443:AAEMfWYjusdNCaMMvQBVOJ_QHwaDoPOWSwY"
WEBAPP_URL = "https://seva02091995.github.io/hamkor-top/?v=5"
OWNER_ID = 7802498650  # telegram id Севары для пересылки заявок
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
USERS_FILE = DATA_DIR / "users.json"
LEADS_FILE = DATA_DIR / "leads.json"

def load_json(path, default=None):
    if default is None: default = {}
    try:
        if path.exists(): return json.loads(path.read_text(encoding='utf-8'))
    except: pass
    return default

def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

try:
    from aiogram import Bot, Dispatcher, types, F
    from aiogram.filters import Command
    from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, MenuButtonWebApp)
    AIOGRAM_AVAILABLE = True
except ImportError:
    AIOGRAM_AVAILABLE = False

async def on_start(message: types.Message):
    user_id = str(message.from_user.id)
    users = load_json(USERS_FILE)
    
    webapp_url = WEBAPP_URL
    if user_id in users:
        # кодируем профиль в URL чтобы Mini App восстановил
        prof = json.dumps(users[user_id], ensure_ascii=False)
        encoded = base64.urlsafe_b64encode(prof.encode('utf-8')).decode('utf-8')
        webapp_url = WEBAPP_URL + '&load=' + encoded
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть Hamkor Top", web_app=WebAppInfo(url=webapp_url))],
        [InlineKeyboardButton(text="📋 Что это?", callback_data="about")]
    ])
    greeting = "🤝 <b>Hamkor Top</b> — твой AI-партнёр для карьеры!\n\n"
    if user_id in users:
        greeting += "✨ Твой профиль уже сохранён. Нажми кнопку чтобы продолжить."
    else:
        greeting += "Свайпай вакансии. Находи работу, сотрудников и нетворкинг.\nСоздано в Узбекистане 🇺🇿"
    
    await message.answer(greeting, reply_markup=kb, parse_mode="HTML")

async def on_about(callback: types.CallbackQuery):
    await callback.message.answer(
        "🎯 <b>Как это работает:</b>\n\n"
        "1. Заполни профиль за 2 минуты\n2. Свайпай карточки\n"
        "3. 👍 Вправо — интересно\n4. 👎 Влево — мимо\n5. Обоюдный интерес = Контакт! 🎉",
        parse_mode="HTML"
    )
    await callback.answer()

async def on_webapp_data(message: types.Message):
    """Принимает данные из Mini App (sendData)"""
    if not message.web_app_data:
        return
    try:
        data = json.loads(message.web_app_data.data)
    except:
        await message.answer("❌ Ошибка формата данных")
        return

    action = data.get("action", "")
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.full_name or user_id

    logging.info(f"WebApp data from {username}: action={action}")

    # --- Сохранение профиля ---
    if action == "saveProfile":
        users = load_json(USERS_FILE)
        users[user_id] = {
            "tg_id": user_id,
            "username": username,
            "name": data.get("name", ""),
            "city": data.get("city", ""),
            "role": data.get("role", ""),
            "skills": data.get("skills", ""),
            "bio": data.get("bio", ""),
            "updated_at": data.get("updatedAt", "")
        }
        save_json(USERS_FILE, users)
        await message.answer("✅ Профиль сохранён!")

    # --- B2B заявка ---
    elif action == "bizLead":
        lead = {
            "tg_id": user_id,
            "username": username,
            "name": data.get("name", ""),
            "contact": data.get("contact", ""),
            "msg": data.get("msg", ""),
            "profile": data.get("profile", {}),
            "ts": data.get("ts", "")
        }
        leads = load_json(LEADS_FILE, [])
        leads.append(lead)
        save_json(LEADS_FILE, leads)

        # Уведомление Севаре
        owner_msg = (
            f"📩 <b>Новая B2B-заявка!</b>\n\n"
            f"👤 <b>Имя:</b> {lead['name']}\n"
            f"📞 <b>Контакт:</b> {lead['contact']}\n"
            f"📝 <b>Запрос:</b> {lead['msg']}\n"
            f"🆔 <b>TG:</b> @{username} ({user_id})"
        )
        try:
            await message.bot.send_message(OWNER_ID, owner_msg, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление: {e}")

        await message.answer("✅ Заявка принята! Мы свяжемся с вами в ближайшее время.")

    # --- AI-запросы ---
    elif action == "aiInterview":
        answers = data.get("answers", [])
        owner_msg = (
            f"🎙️ <b>Результаты AI-интервью от @{username}:</b>\n\n"
            f"1. {answers[0]}\n2. {answers[1]}\n3. {answers[2]}\n4. {answers[3]}\n5. {answers[4]}\n\n"
            f"👤 <b>ID:</b> {user_id}"
        )
        try:
            await message.bot.send_message(OWNER_ID, owner_msg, parse_mode="HTML")
        except: pass
        await message.answer("✅ Интервью пройдено! Мы скоро вернёмся с результатами анализа стиля.")

    else:
        await message.answer("✅ Данные получены")

    await message.bot.send_message(OWNER_ID, 
        f"📨 <b>Hamkor:</b> {username} отправил action=<code>{action}</code>", 
        parse_mode="HTML"
    )

async def main():
    if not AIOGRAM_AVAILABLE:
        os.system("pip install aiogram")
        return
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.message.register(on_start, Command("start"))
    dp.callback_query.register(on_about, lambda c: c.data == "about")
    dp.message.register(on_webapp_data, F.web_app_data)
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="🚀 Hamkor Top", web_app=WebAppInfo(url=WEBAPP_URL))
        )
    except: pass
    print("🤖 Бот @hamkor_top_bot запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
