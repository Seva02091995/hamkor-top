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
FEED_EVENTS_FILE = DATA_DIR / "feed_events.json"
FEED_METRICS_FILE = DATA_DIR / "feed_metrics.json"

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

async def on_avatar_pick(callback: types.CallbackQuery):
    """Выбор AI-аватара: avatar_pick_<index>_<user_id>"""
    parts = callback.data.split('_')
    idx = int(parts[2])
    uid = parts[3]

    users = load_json(USERS_FILE)
    user = users.get(uid, {})
    candidates = user.get("ai_avatar_candidates", [])

    if idx < 0 or idx >= len(candidates):
        await callback.answer("❌ Вариант не найден")
        return

    picked_url = candidates[idx]
    user["avatar_url"] = picked_url
    user.pop("ai_avatar_candidates", None)
    save_json(USERS_FILE, users)

    # Убираем кнопки, показываем выбор
    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ Выбран вариант {idx+1}",
        parse_mode="HTML"
    )

    # Кнопка открытия Mini App с аватаром в URL
    encoded = urllib.parse.quote(picked_url)
    app_url = f"https://seva02091995.github.io/hamkor-top/?v=32&photo={encoded}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть Hamkor Top с новым аватаром", web_app=WebAppInfo(url=app_url))]
    ])
    await callback.message.answer(
        "✨ <b>Аватар установлен!</b>\n\nНажми кнопку ниже чтобы увидеть его в профиле 👇",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer(f"Выбран вариант {idx+1}")

async def on_bio_pick(callback: types.CallbackQuery):
    """Выбор AI-описания: bio_pick_<index>_<user_id>"""
    parts = callback.data.split('_')
    idx = int(parts[2])
    uid = parts[3]

    users = load_json(USERS_FILE)
    user = users.get(uid, {})
    candidates = user.get("ai_bio_candidates", [])

    if idx < 0 or idx >= len(candidates):
        await callback.answer("❌ Вариант не найден")
        return

    picked = candidates[idx]
    user["bio"] = picked
    user.pop("ai_bio_candidates", None)
    save_json(USERS_FILE, users)

    # Кодируем профиль в URL чтобы Mini App подхватил
    prof = json.dumps(user, ensure_ascii=False)
    encoded = base64.urlsafe_b64encode(prof.encode('utf-8')).decode('utf-8')
    app_url = f"https://seva02091995.github.io/hamkor-top/?v=32&load={encoded}"

    await callback.message.edit_text(
        callback.message.text + f"\n✅ <b>Выбран вариант {idx+1}</b>",
        parse_mode="HTML"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть Hamkor Top с новым описанием", web_app=WebAppInfo(url=app_url))]
    ])
    await callback.message.answer(
        "✨ <b>Описание обновлено!</b>\n\nНажми кнопку ниже — профиль сразу откроется с новым текстом 👇",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer(f"Выбран вариант {idx+1}")

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
            "surname": data.get("surname", ""),
            "title": data.get("title", ""),
            "company": data.get("company", ""),
            "skills": data.get("skills", ""),
            "bio": data.get("bio", ""),
            "tg_username": data.get("tgUsername", ""),
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

    # --- События ленты (A/B-метрики) ---
    elif action == "feedEvent":
        events = load_json(FEED_EVENTS_FILE, [])
        events.append({
            "tg_id": user_id,
            "username": username,
            "event": data.get("event", ""),
            "postId": data.get("postId", ""),
            "ab": data.get("ab", "A"),
            "ts": data.get("ts", "")
        })
        save_json(FEED_EVENTS_FILE, events)

        # Агрегация метрик
        metrics = load_json(FEED_METRICS_FILE, {})
        ab = data.get("ab", "A")
        if ab not in metrics:
            metrics[ab] = {"readMore": 0, "detailOpens": 0, "totalUsers": [], "byEvent": {}}
        ev = data.get("event", "")
        if ev:
            if ev not in metrics[ab].get("byEvent", {}):
                metrics[ab].setdefault("byEvent", {})[ev] = 0
            metrics[ab]["byEvent"][ev] += 1
            if ev == "readMore":
                metrics[ab]["readMore"] = metrics[ab].get("readMore", 0) + 1
            elif ev == "detailOpen":
                metrics[ab]["detailOpens"] = metrics[ab].get("detailOpens", 0) + 1
        users_arr = metrics[ab].get("totalUsers", [])
        if user_id not in users_arr:
            users_arr.append(user_id)
        metrics[ab]["totalUsers"] = users_arr
        metrics[ab]["usersCount"] = len(users_arr)
        save_json(FEED_METRICS_FILE, metrics)

    # --- AI-пост ---
    elif action == "aiPost":
        prompt = data.get("prompt", "")
        owner_msg = f"🤖 <b>AI-пост от @{username}:</b>\n\n<code>{prompt[:300]}</code>"
        try: await message.bot.send_message(OWNER_ID, owner_msg, parse_mode="HTML")
        except: pass
        await message.answer("🤖 Генерирую пост... \n\n_Пока AI анализирует твой профиль, попробуй «Интервью со мной» — мы определим твой стиль и все посты станут точнее._", parse_mode="Markdown")

    # --- Публикация мысли в ленту ---
    elif action == "postThought":
        text = data.get("text", "")
        lead = add_to_crm("postThought", user_id, username, data)
        owner_msg = f"✏️ <b>Пост от @{username}:</b>\n\n{text[:500]}"
        try: await message.bot.send_message(OWNER_ID, owner_msg, parse_mode="HTML")
        except: pass
        await message.answer("✅ Мысль опубликована!")

    # --- Отправка поста в канал ---
    elif action == "postToChannel":
        text = data.get("text", "")
        lead = add_to_crm("postToChannel", user_id, username, data)
        owner_msg = f"📤 <b>Пост в канал от @{username}:</b>\n\n{text[:800]}"
        try: await message.bot.send_message(OWNER_ID, owner_msg, parse_mode="HTML")
        except: pass
        await message.answer("✅ Отправлено в канал!")

    # --- Комментарий ---
    elif action == "postComment":
        post_id = data.get("postId", "")
        text = data.get("text", "")
        mentions = data.get("mentions", [])
        add_to_crm("comment", user_id, username, data)
        owner_msg = f"💬 <b>Комментарий от @{username}:</b>\n\nПост: <code>{post_id}</code>\nТекст: {text[:300]}"
        if mentions:
            owner_msg += f"\nУпоминания: {', '.join(mentions[:5])}"
        try: await message.bot.send_message(OWNER_ID, owner_msg, parse_mode="HTML")
        except: pass

    # --- Репост ---
    elif action == "repost":
        post_id = data.get("postId", "")
        with_thought = data.get("withThought", False)
        add_to_crm("repost", user_id, username, data)
        owner_msg = f"🔄 <b>Репост от @{username}:</b> <code>{post_id}</code>" + (" (с мыслью)" if with_thought else "")
        try: await message.bot.send_message(OWNER_ID, owner_msg, parse_mode="HTML")
        except: pass

    # --- Генерация изображения ---
    elif action == "genImage":
        prompt = data.get("prompt", "").strip()
        if not prompt:
            await message.answer("❌ Пустой запрос.")
            return

        await message.answer("🎨 Генерирую изображение... Подожди 10–20 секунд ⏳")

        encoded_prompt = urllib.parse.quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"

        try:
            caption = f"🖼 <b>{prompt[:100]}</b>\n\n_Сгенерировано AI для @{username}_"
            await message.bot.send_photo(
                chat_id=message.chat.id,
                photo=image_url,
                caption=caption,
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Image gen failed: {e}")
            await message.answer(
                "⚠️ Не удалось сгенерировать изображение.\n\n"
                f"Попробуй другой запрос или открой ссылку вручную:\n{image_url}"
            )

        add_to_crm("genImage", user_id, username, data)
        owner_msg = f"🖼 <b>Генерация от @{username}:</b> «{prompt[:120]}»"
        try: await message.bot.send_message(OWNER_ID, owner_msg, parse_mode="HTML")
        except: pass

    # --- AI-аватар ---
    elif action == "aiAvatar":
        style = data.get("style", "business")
        src_photo = data.get("photo", "")
        add_to_crm("aiAvatar", user_id, username, data)

        # Три варианта промптов под разные стили
        base = f"professional profile picture, headshot, centered, good lighting, {style} style, circular crop ready, no text no watermark"
        variants = [
            f"clean corporate headshot, white background, {base}",
            f"modern creative portrait, gradient background, {base}",
            f"casual confident look, natural light, {base}"
        ]

        try:
            # Генерируем и сохраняем URL'ы кандидатов
            urls = []
            for i, v in enumerate(variants):
                enc = urllib.parse.quote(v)
                urls.append(f"https://image.pollinations.ai/prompt/{enc}?width=512&height=512&nologo=true")

            users = load_json(USERS_FILE)
            users[user_id] = users.get(user_id, {})
            users[user_id]["tg_id"] = user_id
            users[user_id]["ai_avatar_candidates"] = urls
            save_json(USERS_FILE, users)

            # Отправляем альбом из 3 фото
            media = []
            for i, url in enumerate(urls):
                cap = f"Вариант {i+1}" if i == 0 else f"Вариант {i+1}"
                media.append(types.InputMediaPhoto(media=url, caption=cap if i == 0 else None))
            await message.bot.send_media_group(message.chat.id, media)

            # Inline-кнопки выбора
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="1️⃣ Вариант 1", callback_data=f"avatar_pick_0_{user_id}"),
                    InlineKeyboardButton(text="2️⃣ Вариант 2", callback_data=f"avatar_pick_1_{user_id}"),
                    InlineKeyboardButton(text="3️⃣ Вариант 3", callback_data=f"avatar_pick_2_{user_id}")
                ]
            ])
            await message.answer("👆 Выбери вариант аватара — он сразу появится в твоём профиле:", reply_markup=kb)

        except Exception as e:
            logging.error(f"AI avatar gen failed: {e}")
            await message.answer("⚠️ Не удалось сгенерировать аватары. Попробуй позже.")

    # --- AI-улучшение описания ---
    elif action == "aiBioImprove":
        bio = data.get("bio", "")
        title = data.get("title", "")
        skills = data.get("skills", "")
        add_to_crm("aiBioImprove", user_id, username, data)

        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        variants = []

        if gemini_key:
            # --- Gemini Free Tier ---
            prompt = (
                "Ты — карьерный коуч. Улучши описание профиля пользователя. "
                f"Должность: {title or 'не указана'}. "
                f"Навыки: {skills or 'не указаны'}. "
                f"Текущее описание: {bio or 'отсутствует'}. "
                "Дай ровно 3 варианта улучшенного описания на русском языке. "
                "Каждый вариант — 2-3 предложения, тёплый профессиональный тон. "
                "Формат ответа строго: три абзаца, разделённых символами '---'."
            )
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
                body = {"contents":[{"parts":[{"text":prompt}]}]}
                req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
                resp = urllib.request.urlopen(req, timeout=25)
                result = json.loads(resp.read())
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                variants = [v.strip() for v in text.split("---") if v.strip()][:3]
            except Exception as e:
                logging.error(f"Gemini bio failed: {e}")

        # Fallback — шаблонные варианты
        if len(variants) < 3:
            t = title or "специалист"
            s = skills or "профессиональные навыки"
            b = bio or ""
            variants = [
                f"{t} с опытом в {s}. {b} Открыт(а) к новым возможностям и сотрудничеству в Узбекистане и за его пределами.".strip(". ")+".",
                f"Профессионал в области {s}. {b} Помогаю компаниям расти через эффективные решения и современный подход.".strip(". ")+".",
                f"Специализируюсь на {s}. {b} Ценю осмысленную работу и долгосрочное партнёрство. Ищу команду, с которой можно создавать ценность.".strip(". ")+"."
            ]

        # Сохраняем кандидатов
        users = load_json(USERS_FILE)
        users[user_id] = users.get(user_id, {})
        users[user_id]["tg_id"] = user_id
        users[user_id]["ai_bio_candidates"] = variants
        save_json(USERS_FILE, users)

        # Отправляем варианты
        text_msg = "✨ <b>Улучшенные варианты описания:</b>\n\n"
        for i, v in enumerate(variants):
            text_msg += f"<b>Вариант {i+1}:</b>\n{v}\n\n"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="1️⃣ Вариант 1", callback_data=f"bio_pick_0_{user_id}"),
                InlineKeyboardButton(text="2️⃣ Вариант 2", callback_data=f"bio_pick_1_{user_id}"),
                InlineKeyboardButton(text="3️⃣ Вариант 3", callback_data=f"bio_pick_2_{user_id}")
            ]
        ])
        await message.answer(text_msg, reply_markup=kb, parse_mode="HTML")

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
    dp.callback_query.register(on_avatar_pick, lambda c: c.data.startswith("avatar_pick_"))
    dp.callback_query.register(on_bio_pick, lambda c: c.data.startswith("bio_pick_"))
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
