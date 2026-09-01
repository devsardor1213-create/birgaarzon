import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import config
import database

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

database.init_db()

admin_sessions = {}

# --- HELPER ---
def get_t(lang, key, **kwargs):
    data = config.get_data()
    texts = data.get('texts', {})
    lang_texts = texts.get(lang, texts.get('uz', {}))
    text = lang_texts.get(key, "")
    if kwargs:
        text = text.format(**kwargs)
    return text

# --- КЛАВИАТУРАЛАР ---
def get_lang_menu():
    kb = [
        [KeyboardButton(text="🇺🇿 O'zbekcha"), KeyboardButton(text="🇷🇺 Русский")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_main_menu(lang):
    kb = [
        [KeyboardButton(text=get_t(lang, 'btn_survey')), KeyboardButton(text=get_t(lang, 'btn_bonus'))],
        [KeyboardButton(text=get_t(lang, 'btn_work')), KeyboardButton(text=get_t(lang, 'btn_about'))],
        [KeyboardButton(text=get_t(lang, 'btn_operator'))]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_menu():
    kb = [
        [KeyboardButton(text="👥 Фойдаланувчилар"), KeyboardButton(text="📝 Сўровномалар")],
        [KeyboardButton(text="💼 Ишга аризалар"), KeyboardButton(text="📢 Хабар юбориш")],
        [KeyboardButton(text="🧑‍💼 Ходимлар"), KeyboardButton(text="⚙️ Созламалар")],
        [KeyboardButton(text="🔙 Бош меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_survey_keyboard(options):
    kb = []
    for i in range(0, len(options), 2):
        row = [KeyboardButton(text=opt) for opt in options[i:i+2]]
        kb.append(row)
    kb.append([KeyboardButton(text="🔙 Ortga")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_decision_keyboard(record_type, record_id):
    kb = [
        [
            InlineKeyboardButton(text="✅ Тасдиқлаш", callback_data=f"{record_type}_app_{record_id}"),
            InlineKeyboardButton(text="❌ Бекор қилиш", callback_data=f"{record_type}_rej_{record_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ҲОЛАТЛАР (FSM) ---
class LangState(StatesGroup):
    waiting_for_lang = State()

class SurveyState(StatesGroup):
    answering = State()

class ApplicationState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_region = State()
    waiting_for_direction = State()

class AdminState(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_broadcast = State()

class AdminSettingsState(StatesGroup):
    waiting_for_promo = State()
    waiting_for_text_edit = State()

class EmployeeState(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_name = State()

class BundleState(StatesGroup):
    waiting_for_combo_name = State()
    waiting_for_product_name = State()
    waiting_for_product_quantity = State()
    waiting_for_more = State()
    waiting_for_target_orders = State()
    waiting_for_images = State()

# --- БУЙРУҚЛАР ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user = message.from_user
    database.save_user(user.id, user.username, user.first_name, user.last_name)
    
    lang = database.get_user_lang(user.id)
    if not lang:
        await message.answer(
            "Tilni tanlang / Выберите язык:",
            reply_markup=get_lang_menu()
        )
        await state.set_state(LangState.waiting_for_lang)
    else:
        await state.clear()
        welcome_text = get_t(lang, 'welcome', name=user.first_name)
        await message.answer(welcome_text, reply_markup=get_main_menu(lang))

@dp.message(LangState.waiting_for_lang)
async def process_lang(message: types.Message, state: FSMContext):
    if message.text == "🇺🇿 O'zbekcha":
        lang = "uz"
    elif message.text == "🇷🇺 Русский":
        lang = "ru"
    else:
        await message.answer("Iltimos, pastdagi tugmalardan birini tanlang.\nПожалуйста, выберите одну из кнопок ниже.")
        return
        
    database.update_user_info(message.from_user.id, lang=lang)
    await state.clear()
    
    welcome_text = get_t(lang, 'welcome', name=message.from_user.first_name)
    await message.answer(welcome_text, reply_markup=get_main_menu(lang))

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    if admin_sessions.get(message.from_user.id):
        await message.answer("Админ панелига хуш келибсиз:", reply_markup=get_admin_menu())
    else:
        await message.answer("Админ логинини киритинг:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(AdminState.waiting_for_login)

@dp.message(AdminState.waiting_for_login)
async def process_admin_login(message: types.Message, state: FSMContext):
    if message.text == config.ADMIN_LOGIN:
        await message.answer("Энди паролни киритинг:")
        await state.set_state(AdminState.waiting_for_password)
    else:
        await message.answer("Логин нотўғри! Қайта уриниб кўринг ёки /start босинг.")
        await state.clear()

@dp.message(AdminState.waiting_for_password)
async def process_admin_password(message: types.Message, state: FSMContext):
    if message.text == config.ADMIN_PASSWORD:
        admin_sessions[message.from_user.id] = True
        await state.clear()
        await message.answer("Пароль тўғри! Админ панелига хуш келибсиз:", reply_markup=get_admin_menu())
    else:
        await message.answer("Нотўғри пароль. Қайта уриниб кўринг ёки /start босинг.")
        await state.clear()

# --- УМУМИЙ ТУГМАЛАР (Икки тилда текширилади) ---
def check_text(msg_text, key):
    data = config.get_data()
    return msg_text in [data['texts'].get('uz', {}).get(key), data['texts'].get('ru', {}).get(key)]

@dp.message(lambda msg: check_text(msg.text, 'btn_about'))
async def about_info(message: types.Message):
    lang = database.get_user_lang(message.from_user.id) or 'uz'
    await message.answer(get_t(lang, 'about_text'), reply_markup=get_main_menu(lang))

@dp.message(lambda msg: check_text(msg.text, 'btn_operator'))
async def operator_contact(message: types.Message):
    lang = database.get_user_lang(message.from_user.id) or 'uz'
    text = get_t(lang, 'operator_text', username=config.OPERATOR_USERNAME)
    await message.answer(text, reply_markup=get_main_menu(lang))

@dp.message(lambda msg: check_text(msg.text, 'btn_bonus'))
async def get_bonus(message: types.Message):
    lang = database.get_user_lang(message.from_user.id) or 'uz'
    has_survey = database.has_completed_survey(message.from_user.id)
    if has_survey:
        data = config.get_data()
        code = data.get('promo_code', 'BIRGA-ARZON')
        text = get_t(lang, 'bonus_has', code=code)
    else:
        text = get_t(lang, 'bonus_none')
    await message.answer(text, reply_markup=get_main_menu(lang))

# --- СЎРОВНОМА ЖАРАЁНИ ---
@dp.message(lambda msg: check_text(msg.text, 'btn_survey'))
async def start_survey(message: types.Message, state: FSMContext):
    lang = database.get_user_lang(message.from_user.id) or 'uz'
    data = config.get_data()
    questions = data.get('questions', {}).get(lang, data['questions'].get('uz', []))
    
    if not questions:
        await message.answer("So'rovnoma savollari topilmadi.")
        return
        
    await state.update_data(current_q=0, answers={}, lang=lang)
    q_data = questions[0]
    await message.answer(
        get_t(lang, 'survey_q', num=1, q=q_data['question']),
        reply_markup=get_survey_keyboard(q_data['options'])
    )
    await state.set_state(SurveyState.answering)

@dp.message(SurveyState.answering)
async def process_survey(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    lang = state_data.get('lang', 'uz')
    if message.text in ["🔙 Ortga", "🔙 Назад", "/start"]:
        await state.clear()
        return await message.answer("Бош меню / Главное меню", reply_markup=get_main_menu(lang))
        
    curr_q_index = state_data['current_q']
    answers = state_data['answers']
    
    data = config.get_data()
    questions = data.get('questions', {}).get(lang, data['questions'].get('uz', []))
    
    q_text = questions[curr_q_index]['question']
    answers[q_text] = message.text
    
    next_q_index = curr_q_index + 1
    
    if next_q_index < len(questions):
        await state.update_data(current_q=next_q_index, answers=answers)
        q_data = questions[next_q_index]
        await message.answer(
            get_t(lang, 'survey_q', num=next_q_index+1, q=q_data['question']),
            reply_markup=get_survey_keyboard(q_data['options'])
        )
    else:
        answers_str = "\n".join([f"- {k}: {v}" for k, v in answers.items()])
        survey_id = database.save_survey(message.from_user.id, answers_str)
        promo_code = data.get('promo_code', 'BIRGA-ARZON')
        
        await message.answer(
            get_t(lang, 'survey_done', code=promo_code),
            reply_markup=get_main_menu(lang)
        )
        
        # Admin xabar
        phone = "Берилмаган"
        region = "Берилмаган"
        
        admin_text = (
            f"🆕 <b>ЯНГИ СЎРОВНОМА</b>\n"
            f"👤 Исм: {message.from_user.first_name}\n"
            f"📱 Телефон: {phone}\n"
            f"📍 Ҳудуд: {region}\n"
            f"🆔 Telegram ID: {message.from_user.id}\n"
            f"🎁 Бонус код: {promo_code}\n"
            f"📝 <b>Сўровнома жавоблари:</b>\n{answers_str}"
        )
        
        kb = get_decision_keyboard("surv", survey_id)
        for admin_id in admin_sessions.keys():
            try:
                await bot.send_message(admin_id, admin_text, reply_markup=kb)
            except:
                pass
        
        await state.clear()

# --- ИШГА АРИЗА ЖАРАЁНИ ---
@dp.message(lambda msg: check_text(msg.text, 'btn_work'))
async def start_application(message: types.Message, state: FSMContext):
    lang = database.get_user_lang(message.from_user.id) or 'uz'
    back_text = "🔙 Ortga" if lang == 'uz' else "🔙 Назад"
    kb = [
        [KeyboardButton(text=get_t(lang, 'btn_phone'), request_contact=True)],
        [KeyboardButton(text=back_text)]
    ]
    markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(
        get_t(lang, 'work_intro'),
        reply_markup=markup
    )
    await state.update_data(lang=lang)
    await state.set_state(ApplicationState.waiting_for_phone)

@dp.message(ApplicationState.waiting_for_phone, F.contact | F.text)
async def process_phone(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    lang = state_data.get('lang', 'uz')
    
    if message.text in ["🔙 Ortga", "🔙 Назад", "/start"]:
        await state.clear()
        return await message.answer("Бош меню / Главное меню", reply_markup=get_main_menu(lang))
        
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text
        
    await state.update_data(phone=phone)
    back_text = "🔙 Ortga" if lang == 'uz' else "🔙 Назад"
    kb = [[KeyboardButton(text=back_text)]]
    await message.answer(get_t(lang, 'ask_region'), reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(ApplicationState.waiting_for_region)

@dp.message(ApplicationState.waiting_for_region)
async def process_region(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    lang = state_data.get('lang', 'uz')
    if message.text in ["🔙 Ortga", "🔙 Назад", "/start"]:
        await state.clear()
        return await message.answer("Бош меню / Главное меню", reply_markup=get_main_menu(lang))
        
    region = message.text
    await state.update_data(region=region)
    
    back_text = "🔙 Ortga" if lang == 'uz' else "🔙 Назад"
    kb = [
        [KeyboardButton(text=get_t(lang, 'dir_1')), KeyboardButton(text=get_t(lang, 'dir_2'))],
        [KeyboardButton(text=get_t(lang, 'dir_3')), KeyboardButton(text=back_text)]
    ]
    markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(get_t(lang, 'ask_dir'), reply_markup=markup)
    await state.set_state(ApplicationState.waiting_for_direction)

@dp.message(ApplicationState.waiting_for_direction)
async def process_direction(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    lang = state_data.get('lang', 'uz')
    
    if message.text in ["🔙 Ortga", "🔙 Назад", "/start"]:
        await state.clear()
        return await message.answer("Бош меню / Главное меню", reply_markup=get_main_menu(lang))
        
    direction = message.text
    phone = state_data.get("phone")
    region = state_data.get("region", "Номаълум")
    lang = state_data['lang']
    
    app_id = database.save_application(message.from_user.id, phone, region, direction)
    
    await message.answer(
        get_t(lang, 'work_done'),
        reply_markup=get_main_menu(lang)
    )
    
    # Admin xabar
    import datetime
    today = datetime.datetime.now().strftime("%d.%m.%Y")
    admin_text = (
        f"🆕 <b>ЯНГИ ИШГА АРИЗА</b>\n"
        f"👤 Исм: {message.from_user.first_name}\n"
        f"📱 Телефон: {phone}\n"
        f"📍 Ҳудуд: {region}\n"
        f"👩‍💻 Йўналиш: {direction}\n"
        f"🆔 Telegram ID: {message.from_user.id}\n"
        f"📅 Сана: {today}"
    )
    
    kb = get_decision_keyboard("app", app_id)
    for admin_id in admin_sessions.keys():
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=kb)
        except:
            pass
            
    await state.clear()

# --- ADMIN TUGMALARI (CALLBACKS) ---
@dp.callback_query(lambda c: c.data.startswith('surv_'))
async def process_survey_decision(callback_query: types.CallbackQuery):
    action, survey_id_str = callback_query.data.split('_')[1:]
    survey_id = int(survey_id_str)
    
    status = "approved" if action == "app" else "rejected"
    database.update_survey_status(survey_id, status)
    
    status_text = "✅ Тасдиқланди" if status == "approved" else "❌ Бекор қилинди"
    new_text = callback_query.message.html_text + f"\n\n<b>Ҳолат:</b> {status_text}"
    await callback_query.message.edit_text(new_text, reply_markup=None)
    
    user_info = database.get_survey_info(survey_id)
    if user_info:
        user_id = user_info[0]
        user_lang = database.get_user_lang(user_id) or 'uz'
        msg_key = "survey_approved" if status == "approved" else "survey_rejected"
        try:
            await bot.send_message(user_id, get_t(user_lang, msg_key))
        except:
            pass

@dp.callback_query(lambda c: c.data.startswith('app_'))
async def process_app_decision(callback_query: types.CallbackQuery):
    action, app_id_str = callback_query.data.split('_')[1:]
    app_id = int(app_id_str)
    
    status = "approved" if action == "app" else "rejected"
    database.update_application_status(app_id, status)
    
    status_text = "✅ Тасдиқланди" if status == "approved" else "❌ Бекор қилинди"
    new_text = callback_query.message.html_text + f"\n\n<b>Ҳолат:</b> {status_text}"
    await callback_query.message.edit_text(new_text, reply_markup=None)
    
    user_info = database.get_application_info(app_id)
    if user_info:
        user_id = user_info[0]
        user_lang = database.get_user_lang(user_id) or 'uz'
        msg_key = "app_approved" if status == "approved" else "app_rejected"
        try:
            await bot.send_message(user_id, get_t(user_lang, msg_key))
        except:
            pass

# --- АДМИН ПАНЕЛ ---
@dp.message(F.text == "🔙 Бош меню")
async def admin_back(message: types.Message):
    lang = database.get_user_lang(message.from_user.id) or 'uz'
    await message.answer("Асосий меню", reply_markup=get_main_menu(lang))

@dp.message(F.text == "👥 Фойдаланувчилар")
async def admin_users(message: types.Message):
    if not admin_sessions.get(message.from_user.id):
        return
    users = database.get_all_users()
    if not users:
        await message.answer("Фойдаланувчилар йўқ.")
        return
    
    text = "👥 Сўнгги фойдаланувчилар:\n\n"
    for u in users:
        text += f"ID: {u[0]} | Исм: {u[2]} | Code: {u[6]}\n"
    await message.answer(text[:4000])

@dp.message(F.text == "📝 Сўровномалар")
async def admin_surveys(message: types.Message):
    if not admin_sessions.get(message.from_user.id):
        return
    surveys = database.get_pending_surveys()
    if not surveys:
        await message.answer("Янги (кутилаётган) сўровномалар йўқ.")
        return
        
    await message.answer(f"📝 Кутилаётган сўровномалар: {len(surveys)} та")
    
    for s in surveys:
        s_id = s[0]
        first_name = s[1]
        answers_str = s[2]
        date = s[4]
        
        text = (
            f"📝 <b>СЎРОВНОМА</b> (ID: {s_id})\n"
            f"👤 Исм: {first_name}\n"
            f"📅 Сана: {date}\n"
            f"<b>Жавоблар:</b>\n{answers_str}"
        )
        kb = get_decision_keyboard("surv", s_id)
        await message.answer(text, reply_markup=kb)
        await asyncio.sleep(0.1)

@dp.message(F.text == "💼 Ишга аризалар")
async def admin_apps(message: types.Message):
    if not admin_sessions.get(message.from_user.id):
        return
    apps = database.get_pending_applications()
    if not apps:
        await message.answer("Янги (кутилаётган) аризалар йўқ.")
        return
        
    await message.answer(f"💼 Кутилаётган аризалар: {len(apps)} та")
    
    for a in apps:
        a_id = a[0]
        first_name = a[1]
        phone = a[2]
        region = a[3]
        direction = a[4]
        date = a[6]
        
        text = (
            f"💼 <b>ИШГА АРИЗА</b> (ID: {a_id})\n"
            f"👤 Исм: {first_name}\n"
            f"📱 Телефон: {phone}\n"
            f"📍 Ҳудуд: {region}\n"
            f"👩‍💻 Йўналиш: {direction}\n"
            f"📅 Сана: {date}"
        )
        kb = get_decision_keyboard("app", a_id)
        await message.answer(text, reply_markup=kb)
        await asyncio.sleep(0.1)

@dp.message(F.text == "📢 Хабар юбориш")
async def admin_broadcast_start(message: types.Message, state: FSMContext):
    if not admin_sessions.get(message.from_user.id):
        return
    await message.answer("📢 Барча фойдаланувчиларга юбориш учун хабар матнини киритинг:\n(Бекор қилиш учун /start босинг)", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AdminState.waiting_for_broadcast)

@dp.message(AdminState.waiting_for_broadcast)
async def admin_broadcast_send(message: types.Message, state: FSMContext):
    if message.text == '/start':
        await state.clear()
        lang = database.get_user_lang(message.from_user.id) or 'uz'
        await message.answer("Бекор қилинди.", reply_markup=get_main_menu(lang))
        return
        
    text_to_send = message.text
    user_ids = database.get_all_telegram_ids()
    sent_count = 0
    
    await message.answer("Хабар юборилмоқда, илтимос кутинг...")
    
    for uid in user_ids:
        try:
            await bot.send_message(uid, text_to_send)
            sent_count += 1
            await asyncio.sleep(0.05)
        except:
            pass
            
    await message.answer(f"✅ Хабар {sent_count} та фойдаланувчига муваффақиятли юборилди!", reply_markup=get_admin_menu())
    await state.clear()

# --- СОЗЛАМАЛАР ---
@dp.message(F.text == "⚙️ Созламалар")
async def admin_settings(message: types.Message):
    if not admin_sessions.get(message.from_user.id):
        return
    kb = [
        [InlineKeyboardButton(text="🎁 Промокодни ўзгартириш", callback_data="settings_promo")],
        [InlineKeyboardButton(text="📝 Матнларни ўзгартириш (Тез кунда)", callback_data="settings_soon")]
    ]
    await message.answer("⚙️ Созламалар бўлимига хуш келибсиз. Нимани таҳрирламоқчисиз?", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(lambda c: c.data == "settings_promo")
async def process_settings_promo(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer("🎁 Янги умумий промокодни юборинг (масалан: KUZ-2024):")
    await state.set_state(AdminSettingsState.waiting_for_promo)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "settings_soon")
async def process_settings_soon(callback_query: types.CallbackQuery, state: FSMContext):
    data = config.get_data()
    uz_texts = data.get('texts', {}).get('uz', {})
    
    kb = []
    keys = list(uz_texts.keys())
    for i in range(0, len(keys), 2):
        row = []
        for k in keys[i:i+2]:
            row.append(InlineKeyboardButton(text=k, callback_data=f"edit_text_{k}"))
        kb.append(row)
        
    await callback_query.message.edit_text("Ўзгартирмоқчи бўлган матнни танланг (UZ):", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(lambda c: c.data.startswith("edit_text_"))
async def process_edit_text_select(callback_query: types.CallbackQuery, state: FSMContext):
    key = callback_query.data.replace("edit_text_", "")
    data = config.get_data()
    current_text = data.get('texts', {}).get('uz', {}).get(key, "")
    
    await state.update_data(editing_key=key)
    await callback_query.message.answer(f"Ҳозирги матн ({key}):\n\n{current_text}\n\nЯнги матнни юборинг (Бекор қилиш учун /start):")
    await state.set_state(AdminSettingsState.waiting_for_text_edit)
    await callback_query.answer()

@dp.message(AdminSettingsState.waiting_for_text_edit)
async def process_save_text(message: types.Message, state: FSMContext):
    if message.text == '/start':
        await state.clear()
        await message.answer("Бекор қилинди.", reply_markup=get_admin_menu())
        return
        
    state_data = await state.get_data()
    key = state_data.get('editing_key')
    
    data = config.get_data()
    if 'texts' not in data:
        data['texts'] = {}
    if 'uz' not in data['texts']:
        data['texts']['uz'] = {}
        
    data['texts']['uz'][key] = message.html_text
    config.save_data(data)
    
    await message.answer(f"✅ Матн муваффақиятли ўзгартирилди ({key})!", reply_markup=get_admin_menu())
    await state.clear()

@dp.message(AdminSettingsState.waiting_for_promo)
async def save_new_promo(message: types.Message, state: FSMContext):
    new_promo = message.text
    data = config.get_data()
    data['promo_code'] = new_promo
    config.save_data(data)
    await message.answer(f"✅ Промокод муваффақиятли ўзгартирилди!\nЯнги код: <b>{new_promo}</b>", reply_markup=get_admin_menu())
    await message.answer(f"✅ Промокод муваффақиятли ўзгартирилди!\nЯнги код: <b>{new_promo}</b>", reply_markup=get_admin_menu())
    await state.clear()

# --- ADMIN: EMPLOYEES ---
@dp.message(F.text == "🧑‍💼 Ходимлар")
async def admin_employees_menu(message: types.Message):
    if not admin_sessions.get(message.from_user.id):
        return
    kb = [
        [KeyboardButton(text="➕ Ходим қўшиш"), KeyboardButton(text="📋 Ходимлар рўйхати")],
        [KeyboardButton(text="🔙 Бош меню")]
    ]
    await message.answer("🧑‍💼 Ходимлар бўлими:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.text == "➕ Ходим қўшиш")
async def admin_add_employee(message: types.Message):
    if not admin_sessions.get(message.from_user.id):
        return
    import random, string
    login = ''.join(random.choices(string.ascii_lowercase, k=3))
    password = ''.join(random.choices(string.digits, k=3))
    database.add_employee(login, password)
    await message.answer(f"✅ Янги ходим яратилди!\n\n🔑 Логин: {login}\n🔒 Пароль: {password}\n\nУшбу маълумотларни ходимга беринг. Улар /xodim буйруғи орқали киришлари мумкин.")

@dp.message(F.text == "📋 Ходимлар рўйхати")
async def admin_employee_list(message: types.Message):
    if not admin_sessions.get(message.from_user.id):
        return
    employees = database.get_all_employees()
    if not employees:
        await message.answer("Ходимлар йўқ.")
        return
    kb = []
    for emp in employees:
        emp_id, login, pwd, name, tg_id = emp
        btn_text = f"👤 {name or 'Исмсиз'} ({login})"
        kb.append([InlineKeyboardButton(text=btn_text, callback_data=f"chk_emp_{emp_id}")])
    await message.answer("📋 Ходимлар рўйхати. Текшириш учун устига босинг:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(lambda c: c.data.startswith("chk_emp_"))
async def admin_check_employee(callback_query: types.CallbackQuery):
    emp_id = int(callback_query.data.split('_')[2])
    emp = database.get_employee_by_id(emp_id)
    if not emp:
        await callback_query.answer("Ходим топилмади", show_alert=True)
        return
    stats = database.get_employee_stats(emp_id)
    text = f"🧑‍💼 <b>Ходим маълумотлари</b>\n\nИсм: {emp[3] or 'Кўрсатилмаган'}\nЛогин: {emp[1]}\nПароль: {emp[2]}\n\n📊 <b>Статистика:</b>\nҚўшилган маҳсулотлар: {stats['count']} та\nУмумий сумма: {stats['total']:,.0f} сўм"
    await callback_query.message.edit_text(text)

# --- EMPLOYEE BOT SIDE ---
@dp.message(Command("xodim"))
async def cmd_xodim(message: types.Message, state: FSMContext):
    emp = database.get_employee_by_tg_id(message.from_user.id)
    if emp:
        await show_employee_menu(message)
    else:
        await message.answer("Ходимлар панелига кириш учун логинни киритинг:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(EmployeeState.waiting_for_login)

@dp.message(EmployeeState.waiting_for_login)
async def process_emp_login(message: types.Message, state: FSMContext):
    await state.update_data(emp_login=message.text)
    await message.answer("Паролни киритинг:")
    await state.set_state(EmployeeState.waiting_for_password)

@dp.message(EmployeeState.waiting_for_password)
async def process_emp_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    login = data.get("emp_login")
    password = message.text
    emp = database.get_employee_by_credentials(login, password)
    if emp:
        await state.update_data(emp_id=emp[0])
        if emp[3]: # name exists
            database.update_employee_info(emp[0], emp[3], message.from_user.id)
            await state.clear()
            await show_employee_menu(message)
        else:
            await message.answer("Тизимга муваффақиятли кирдингиз! Илтимос, исмингизни киритинг:")
            await state.set_state(EmployeeState.waiting_for_name)
    else:
        await message.answer("Логин ёки пароль нотўғри! /xodim ни босиб қайта уриниб кўринг.")
        await state.clear()

@dp.message(EmployeeState.waiting_for_name)
async def process_emp_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    emp_id = data.get("emp_id")
    database.update_employee_info(emp_id, message.text, message.from_user.id)
    await message.answer(f"Хуш келибсиз, {message.text}!")
    await state.clear()
    await show_employee_menu(message)

async def show_employee_menu(message: types.Message):
    kb = [
        [KeyboardButton(text="➕ Маҳсулот қўшиш"), KeyboardButton(text="📦 Менинг тўпламларим")]
    ]
    await message.answer("Ходимлар менюси:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.text == "➕ Маҳсулот қўшиш")
async def emp_add_bundle(message: types.Message, state: FSMContext):
    emp = database.get_employee_by_tg_id(message.from_user.id)
    if not emp: return
    await state.update_data(items=[], images=[])
    kb = [[KeyboardButton(text="Bekor")]]
    text = "<b>Yangi yig'im</b>\n\nCombo nomi:\n\n<i>«Har bir to'plamga» — odatda 1. 122 yozsangiz, 1 to'plam uchun ombordan 122 dona ketadi. Omborda shuncha bo'lmasa, mijozga «qolmagan» chiqadi.</i>"
    await message.answer(text, reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(BundleState.waiting_for_combo_name)

@dp.message(BundleState.waiting_for_combo_name)
async def emp_bundle_name(message: types.Message, state: FSMContext):
    if message.text == "Bekor":
        await state.clear()
        return await show_employee_menu(message)
    await state.update_data(combo_name=message.text)
    data = await state.get_data()
    idx = len(data.get('items', [])) + 1
    kb = [[KeyboardButton(text="Bekor")]]
    await message.answer(f"Mahsulot {idx} (Tanlang yoki yozing):", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(BundleState.waiting_for_product_name)

@dp.message(BundleState.waiting_for_product_name)
async def emp_bundle_prod_name(message: types.Message, state: FSMContext):
    if message.text == "Bekor":
        await state.clear()
        return await show_employee_menu(message)
    await state.update_data(current_product=message.text)
    kb = [[KeyboardButton(text="Bekor")]]
    await message.answer(f"Har bir to'plamga (miqdori):", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(BundleState.waiting_for_product_quantity)

@dp.message(BundleState.waiting_for_product_quantity)
async def emp_bundle_prod_qty(message: types.Message, state: FSMContext):
    if message.text == "Bekor":
        await state.clear()
        return await show_employee_menu(message)
    try:
        qty = int(message.text.strip())
    except:
        await message.answer("Iltimos, faqat raqam kiriting!")
        return
        
    data = await state.get_data()
    items = data.get('items', [])
    items.append({'name': data['current_product'], 'quantity': qty})
    await state.update_data(items=items)
    
    kb = [
        [InlineKeyboardButton(text="➕ Mahsulot qo'shish", callback_data="add_more_yes")],
        [InlineKeyboardButton(text="Davom etish ➡️", callback_data="add_more_no")]
    ]
    await message.answer("Qo'shildi. Yana qo'shasizmi?", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(BundleState.waiting_for_more)

@dp.callback_query(BundleState.waiting_for_more)
async def emp_bundle_more(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "add_more_yes":
        data = await state.get_data()
        idx = len(data.get('items', [])) + 1
        await callback_query.message.delete()
        kb = [[KeyboardButton(text="Bekor")]]
        await callback_query.message.answer(f"Mahsulot {idx} (Tanlang yoki yozing):", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        await state.set_state(BundleState.waiting_for_product_name)
    elif callback_query.data == "add_more_no":
        await callback_query.message.delete()
        kb = [[KeyboardButton(text="Bekor")]]
        text = "<b>Maqsad (buyurtma)</b>\n\n<i>Bu ombor emas. Nechta buyurtma yig'ilishini ko'rsatadi. Yig'imni yopish qo'lda — «Yopish» tugmasi bilan.</i>"
        await callback_query.message.answer(text, reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        await state.set_state(BundleState.waiting_for_target_orders)
    await callback_query.answer()

@dp.message(BundleState.waiting_for_target_orders)
async def emp_bundle_target(message: types.Message, state: FSMContext):
    if message.text == "Bekor":
        await state.clear()
        return await show_employee_menu(message)
    try:
        target = int(message.text.strip())
    except:
        await message.answer("Iltimos, faqat raqam kiriting!")
        return
    await state.update_data(target_orders=target)
    
    kb = [[KeyboardButton(text="Bekor"), KeyboardButton(text="Ochish")]]
    text = "<b>Rasmlar</b>\nKamida 1 ta, ko'pi bilan 5 ta. Birinchisi — cover.\n\nRasmlarni yuboring, tugatgach «Ochish» tugmasini bosing:"
    await message.answer(text, reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(BundleState.waiting_for_images)

@dp.message(BundleState.waiting_for_images, F.photo)
async def emp_bundle_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    images = data.get('images', [])
    if len(images) < 5:
        # Get highest resolution photo
        images.append(message.photo[-1].file_id)
        await state.update_data(images=images)
        await message.answer(f"Rasm qabul qilindi ({len(images)}/5). Yana yuborish yoki «Ochish» ni bosing.")
    else:
        await message.answer("Siz allaqachon maksimal (5 ta) rasm yubordingiz. «Ochish» tugmasini bosing.")

@dp.message(BundleState.waiting_for_images, F.text.in_(["Ochish", "Bekor"]))
async def emp_bundle_save(message: types.Message, state: FSMContext):
    if message.text == "Bekor":
        await state.clear()
        return await show_employee_menu(message)
        
    data = await state.get_data()
    images = data.get('images', [])
    if not images:
        await message.answer("Iltimos, kamida 1 ta rasm yuboring!")
        return
        
    emp = database.get_employee_by_tg_id(message.from_user.id)
    database.add_bundle(
        employee_id=emp[0],
        combo_name=data['combo_name'],
        target_orders=data['target_orders'],
        items=data['items'],
        image_file_ids=images
    )
    
    await message.answer("✅ Yangi yig'im muvaffaqiyatli ochildi!", reply_markup=ReplyKeyboardRemove())
    await state.clear()
    await show_employee_menu(message)

@dp.message(F.text == "📦 Менинг тўпламларим")
async def emp_collections(message: types.Message):
    emp = database.get_employee_by_tg_id(message.from_user.id)
    if not emp: return
    bundles = database.get_employee_bundles(emp[0])
    if not bundles:
        await message.answer("Сизда ҳозирча тўпламлар йўқ.")
        return
    stats = database.get_employee_bundle_stats(emp[0])
    text = f"📦 <b>Сизнинг тўпламларингиз:</b>\nУмумий сони: {stats['count']}\n\n"
    for b in bundles[:10]: # show last 10
        text += f"🔹 <b>{b['combo_name']}</b> (Maqsad: {b['target_orders']} ta)\n"
        for item in b['items']:
            text += f"   - {item[0]}: {item[1]} ta\n"
        text += f"   🖼 Rasmlar: {len(b['images'])} ta\n\n"
    
    kb = [[InlineKeyboardButton(text="🌐 Сайтга ўтиш", url="https://mydiller.uz/")]]
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

async def main():
    print("Бот ишга тушди...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
