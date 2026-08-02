"""
Hamkor Top — Telegram Bot + Mini App Server
Принимает данные из Mini App, сохраняет профили, пересылает B2B-заявки.
"""
import asyncio, json, os, logging, base64, urllib.parse
from pathlib import Path

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8877540443:AAEMfWYjusdNCaMMvQBVOJ_QHwaDoPOWSwY"
WEBAPP_URL = "https://seva02091995.github.io/hamkor-top/?v=23"
OWNER_ID = 7802498650  # telegram id Севары для пересылки заявок
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
USERS_FILE = DATA_DIR / "users.json"
LEADS_HUB_FILE = DATA_DIR / "leads_hub.json"

def add_to_crm(lead_type, user_id, username, data):
    leads = load_json(LEADS_HUB_FILE, [])
    new_lead = {
        "id": len(leads) + 1,
        "type": lead_type,
        "tg_id": user_id,
        "username": username,
        "status": "new",
        "data": data,
        "created_at": data.get("ts", "")
    }
    leads.append(new_lead)
    save_json(LEADS_HUB_FILE, leads)
    return new_lead

INTERVIEW_DRAFTS_FILE = DATA_DIR / "interview_drafts.json"
TONE_PROFILES_FILE = DATA_DIR / "tone_profiles.json"

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

async def on_crm_callback(callback: types.CallbackQuery):
    if not callback.data.startswith("crm_status_"): return
    parts = callback.data.split('_')
    lead_id = int(parts[2])
    new_status = parts[3]
    
    leads = load_json(LEADS_HUB_FILE, [])
    for lead in leads:
        if lead['id'] == lead_id:
            lead['status'] = new_status
            break
    save_json(LEADS_HUB_FILE, leads)
    
    await callback.message.edit_text(callback.message.text + f"\n\n⚙️ <b>Статус:</b> {new_status}", parse_mode="HTML")
    await callback.answer(f"Статус изменен на {new_status}")

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

    # --- B2B заявка (CRM) ---
    elif action == "bizLead":
        lead = add_to_crm("biz", user_id, username, data)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ В работу", callback_data=f"crm_status_{lead['id']}_progress")],
            [InlineKeyboardButton(text="🎯 Закрыть", callback_data=f"crm_status_{lead['id']}_done")]
        ])
        owner_msg = (
            f"📩 <b>#CRM Заявка (Бизнес):</b> #{lead['id']}\n\n"
            f"👤 {data.get('name')} (@{username})\n"
            f"📞 {data.get('contact')}\n"
            f"📝 {data.get('msg')}"
        )
        await message.bot.send_message(OWNER_ID, owner_msg, reply_markup=kb, parse_mode="HTML")
        await message.answer("✅ Заявка принята!")

    # --- Проблема/Идея (CRM) ---
    elif action == "issue":
        lead = add_to_crm("issue", user_id, username, data)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ В работу", callback_data=f"crm_status_{lead['id']}_progress")],
            [InlineKeyboardButton(text="🎯 Закрыть", callback_data=f"crm_status_{lead['id']}_done")]
        ])
        owner_msg = (
            f"💡 <b>#CRM Заявка (Issue):</b> #{lead['id']}\n\n"
            f"👤 @{username}\n"
            f"📝 {data.get('msg')}\n"
            f"📞 {data.get('contact')}"
        )
        await message.bot.send_message(OWNER_ID, owner_msg, reply_markup=kb, parse_mode="HTML")
        await message.answer("✅ Спасибо, мы скоро ответим!")

    # --- Черновик интервью ---
    elif action == "interviewDraftSave":
        drafts = load_json(INTERVIEW_DRAFTS_FILE, {})
        drafts[user_id] = {
            "tg_id": user_id,
            "username": username,
            "draft": data.get("draft", {}),
            "updated_at": data.get("updated_at", "")
        }
        save_json(INTERVIEW_DRAFTS_FILE, drafts)

    elif action == "interviewDraftClear":
        drafts = load_json(INTERVIEW_DRAFTS_FILE, {})
        if user_id in drafts:
            del drafts[user_id]
            save_json(INTERVIEW_DRAFTS_FILE, drafts)

    # --- Сохранение tone-профиля ---
    elif action == "toneProfileSave":
        profile = data.get("profile", {})
        answers = data.get("answers", [])

        tones = load_json(TONE_PROFILES_FILE, {})
        tones[user_id] = {
            "tg_id": user_id,
            "username": username,
            "profile": profile,
            "answers": answers
        }
        save_json(TONE_PROFILES_FILE, tones)

        users = load_json(USERS_FILE, {})
        if user_id not in users:
            users[user_id] = {"tg_id": user_id, "username": username}
        users[user_id]["tone_profile"] = profile
        save_json(USERS_FILE, users)

        owner_msg = (
            f"🎙️ <b>Tone Profile сохранён:</b> @{username}\n\n"
            f"🧠 <b>Стиль:</b> {profile.get('main','Нейтральный')}\n"
            f"🔑 <b>Ключи:</b> {', '.join(profile.get('keys', []))}\n"
            f"👤 <b>ID:</b> {user_id}"
        )
        try:
            await message.bot.send_message(OWNER_ID, owner_msg, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Не удалось отправить tone profile: {e}")

    # --- Legacy AI interview ---
    elif action == "aiInterview":
        answers = data.get("answers", [])
        owner_msg = (
            f"🎙️ <b>Результаты AI-интервью от @{username}:</b>\n\n"
            f"1. {answers[0] if len(answers)>0 else ''}\n2. {answers[1] if len(answers)>1 else ''}\n3. {answers[2] if len(answers)>2 else ''}\n4. {answers[3] if len(answers)>3 else ''}\n5. {answers[4] if len(answers)>4 else ''}\n\n"
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
    dp.callback_query.register(on_crm_callback, lambda c: c.data.startswith("crm_status_"))
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
