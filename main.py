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
        [KeyboardButton(text="🇺🇿 O'zbekcha")],
        [KeyboardButton(text="🇷🇺 Русский")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_main_menu(lang):
    kb = [
        [KeyboardButton(text=get_t(lang, 'btn_survey'))],
        [KeyboardButton(text=get_t(lang, 'btn_bonus'))],
        [KeyboardButton(text=get_t(lang, 'btn_work'))],
        [KeyboardButton(text=get_t(lang, 'btn_about'))],
        [KeyboardButton(text=get_t(lang, 'btn_operator'))]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_menu():
    kb = [
        [KeyboardButton(text="👥 Фойдаланувчилар"), KeyboardButton(text="📝 Сўровномалар")],
        [KeyboardButton(text="💼 Ишга аризалар"), KeyboardButton(text="📢 Хабар юбориш")],
        [KeyboardButton(text="⚙️ Созламалар"), KeyboardButton(text="🔙 Бош меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_survey_keyboard(options):
    kb = [[KeyboardButton(text=opt)] for opt in options]
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
    curr_q_index = state_data['current_q']
    answers = state_data['answers']
    lang = state_data['lang']
    
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
    kb = [[KeyboardButton(text=get_t(lang, 'btn_phone'), request_contact=True)]]
    markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(
        get_t(lang, 'work_intro'),
        reply_markup=markup
    )
    await state.update_data(lang=lang)
    await state.set_state(ApplicationState.waiting_for_phone)

@dp.message(ApplicationState.waiting_for_phone, F.contact | F.text)
async def process_phone(message: types.Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text
        
    await state.update_data(phone=phone)
    state_data = await state.get_data()
    lang = state_data['lang']
    
    await message.answer(get_t(lang, 'ask_region'), reply_markup=ReplyKeyboardRemove())
    await state.set_state(ApplicationState.waiting_for_region)

@dp.message(ApplicationState.waiting_for_region)
async def process_region(message: types.Message, state: FSMContext):
    region = message.text
    await state.update_data(region=region)
    state_data = await state.get_data()
    lang = state_data['lang']
    
    kb = [
        [KeyboardButton(text=get_t(lang, 'dir_1'))],
        [KeyboardButton(text=get_t(lang, 'dir_2'))],
        [KeyboardButton(text=get_t(lang, 'dir_3'))]
    ]
    markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(get_t(lang, 'ask_dir'), reply_markup=markup)
    await state.set_state(ApplicationState.waiting_for_direction)

@dp.message(ApplicationState.waiting_for_direction)
async def process_direction(message: types.Message, state: FSMContext):
    direction = message.text
    state_data = await state.get_data()
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
async def process_settings_soon(callback_query: types.CallbackQuery):
    await callback_query.answer("Матнларни ва саволларни бот орқали ўзгартириш устида ишланмоқда. Ҳозирча data.json орқали ўзгартиришингиз мумкин.", show_alert=True)

@dp.message(AdminSettingsState.waiting_for_promo)
async def save_new_promo(message: types.Message, state: FSMContext):
    new_promo = message.text
    data = config.get_data()
    data['promo_code'] = new_promo
    config.save_data(data)
    await message.answer(f"✅ Промокод муваффақиятли ўзгартирилди!\nЯнги код: <b>{new_promo}</b>", reply_markup=get_admin_menu())
    await state.clear()

async def main():
    print("Бот ишга тушди...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
