import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
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

def get_main_menu(lang, telegram_id=None):
    kb = [
        [KeyboardButton(text=get_t(lang, 'btn_survey')), KeyboardButton(text=get_t(lang, 'btn_bonus'))],
        [KeyboardButton(text=get_t(lang, 'btn_work')), KeyboardButton(text=get_t(lang, 'btn_about'))],
        [KeyboardButton(text=get_t(lang, 'btn_operator'))]
    ]
    if telegram_id and database.get_user_is_employee(telegram_id):
        kb.append([KeyboardButton(text="🧑‍💻 Xodimlar bo'limi")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_menu():
    kb = [
        [KeyboardButton(text="👥 Фойдаланувчилар"), KeyboardButton(text="📝 Сўровномалар")],
        [KeyboardButton(text="💼 Ишга аризалар"), KeyboardButton(text="📢 Хабар юбориш")],
        [KeyboardButton(text="⚙️ Созламалар"), KeyboardButton(text="🔙 Бош меню")]
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
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_address = State()
    waiting_for_direction = State()

class AdminState(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_broadcast = State()

class AdminSettingsState(StatesGroup):
    waiting_for_promo = State()
    waiting_for_text_edit = State()

class ProductState(StatesGroup):
    waiting_for_name = State()
    waiting_for_photo = State()
    waiting_for_price = State()

# --- БУЙРУҚЛАР ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext, command: CommandObject = None):
    user = message.from_user
    if user.id == config.ADMIN_ID:
        admin_sessions[user.id] = True
        await message.answer("Асосий админ менюси:", reply_markup=get_admin_menu())
        return
        
    referrer_id = None
    if command and command.args:
        try:
            ref_id = int(command.args)
            if ref_id != user.id:
                referrer_id = ref_id
        except ValueError:
            pass

    is_new, is_new_referral = database.save_user(user.id, user.username, user.first_name, user.last_name, referrer_id)
    
    if is_new_referral and referrer_id:
        try:
            count = len(database.get_referrals(referrer_id))
            await bot.send_message(referrer_id, f"🎉 Sizda yangi a'zo qo'shildi: {user.first_name}!\nJami a'zolaringiz: {count} ta.")
        except:
            pass
            
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
        await message.answer(welcome_text, reply_markup=get_main_menu(lang, user.id))

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
    await message.answer(welcome_text, reply_markup=get_main_menu(lang, message.from_user.id))

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    if message.from_user.id == config.ADMIN_ID:
        admin_sessions[message.from_user.id] = True
        await message.answer("Админ панелига хуш келибсиз:", reply_markup=get_admin_menu())
    else:
        await message.answer("Сизда админ ҳуқуқлари йўқ.")

# --- УМУМИЙ ТУГМАЛАР (Икки тилда текширилади) ---
def check_text(msg_text, key):
    data = config.get_data()
    return msg_text in [data['texts'].get('uz', {}).get(key), data['texts'].get('ru', {}).get(key)]

@dp.message(lambda msg: check_text(msg.text, 'btn_about'))
async def about_info(message: types.Message):
    lang = database.get_user_lang(message.from_user.id) or 'uz'
    await message.answer(get_t(lang, 'about_text'), reply_markup=get_main_menu(lang, message.from_user.id))

@dp.message(lambda msg: check_text(msg.text, 'btn_operator'))
async def operator_contact(message: types.Message):
    lang = database.get_user_lang(message.from_user.id) or 'uz'
    text = get_t(lang, 'operator_text', username=config.OPERATOR_USERNAME)
    await message.answer(text, reply_markup=get_main_menu(lang, message.from_user.id))

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
    await message.answer(text, reply_markup=get_main_menu(lang, message.from_user.id))

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
    curr_q_index = state_data['current_q']
    answers = state_data['answers']
    
    data = config.get_data()
    questions = data.get('questions', {}).get(lang, data['questions'].get('uz', []))

    if message.text in ["🔙 Ortga", "🔙 Назад", "/start"]:
        if curr_q_index > 0:
            prev_q_index = curr_q_index - 1
            await state.update_data(current_q=prev_q_index)
            prev_q_text = questions[prev_q_index]['question']
            if prev_q_text in answers:
                del answers[prev_q_text]
            await state.update_data(answers=answers)
            q_data = questions[prev_q_index]
            return await message.answer(
                get_t(lang, 'survey_q', num=prev_q_index+1, q=q_data['question']),
                reply_markup=get_survey_keyboard(q_data['options'])
            )
        else:
            await state.clear()
            return await message.answer("Бош меню / Главное меню", reply_markup=get_main_menu(lang, message.from_user.id))
    
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
            reply_markup=get_main_menu(lang, message.from_user.id)
        )
        
        # Admin xabar
        phone = "Берилмаган"
        region = "Берилмаган"
        
        username = f"@{message.from_user.username}" if message.from_user.username else "Йўқ"
        admin_text = (
            f"🆕 <b>ЯНГИ СЎРОВНОМА</b>\n"
            f"👤 Исм: {message.from_user.first_name}\n"
            f"🔗 Username: {username}\n"
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
        [KeyboardButton(text=back_text)]
    ]
    markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    text = "📝 Ism va familiyangizni kiriting:" if lang == 'uz' else "📝 Введите ваше имя и фамилию:"
    await message.answer(text, reply_markup=markup)
    await state.update_data(lang=lang)
    await state.set_state(ApplicationState.waiting_for_name)

@dp.message(ApplicationState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    lang = state_data.get('lang', 'uz')
    
    if message.text in ["🔙 Ortga", "🔙 Назад", "/start"]:
        await state.clear()
        return await message.answer("Бош меню / Главное меню", reply_markup=get_main_menu(lang, message.from_user.id))
        
    await state.update_data(name=message.text)
    text = "Yoshingizni kiriting:" if lang == 'uz' else "Введите ваш возраст:"
    await message.answer(text)
    await state.set_state(ApplicationState.waiting_for_age)

@dp.message(ApplicationState.waiting_for_age)
async def process_age(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    lang = state_data.get('lang', 'uz')
    
    if message.text in ["🔙 Ortga", "🔙 Назад", "/start"]:
        text = "📝 Ism va familiyangizni kiriting:" if lang == 'uz' else "📝 Введите ваше имя и фамилию:"
        await message.answer(text)
        return await state.set_state(ApplicationState.waiting_for_name)
        
    await state.update_data(age=message.text)
    text = "Yashash manzilingizni kiriting:" if lang == 'uz' else "Введите ваш адрес проживания:"
    await message.answer(text)
    await state.set_state(ApplicationState.waiting_for_address)

@dp.message(ApplicationState.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    lang = state_data.get('lang', 'uz')
    
    if message.text in ["🔙 Ortga", "🔙 Назад", "/start"]:
        text = "Yoshingizni kiriting:" if lang == 'uz' else "Введите ваш возраст:"
        await message.answer(text)
        return await state.set_state(ApplicationState.waiting_for_age)
        
    await state.update_data(address=message.text)
    
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
        text = "Yashash manzilingizni kiriting:" if lang == 'uz' else "Введите ваш адрес проживания:"
        back_text = "🔙 Ortga" if lang == 'uz' else "🔙 Назад"
        kb = [[KeyboardButton(text=back_text)]]
        markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        await message.answer(text, reply_markup=markup)
        return await state.set_state(ApplicationState.waiting_for_address)
        
    direction = message.text
    name = state_data.get("name")
    age = state_data.get("age")
    address = state_data.get("address")
    
    app_id = database.save_application(message.from_user.id, name, age, address, direction)
    
    await message.answer(
        get_t(lang, 'work_done'),
        reply_markup=get_main_menu(lang, message.from_user.id)
    )
    
    # Admin xabar
    import datetime
    today = datetime.datetime.now().strftime("%d.%m.%Y")
    username = f"@{message.from_user.username}" if message.from_user.username else "Йўқ"
    admin_text = (
        f"🆕 <b>ЯНГИ ИШГА АРИЗА</b>\n"
        f"👤 Исм/Фамилия: {name}\n"
        f"🎂 Ёши: {age}\n"
        f"📍 Манзил: {address}\n"
        f"👩‍💻 Йўналиш: {direction}\n"
        f"🔗 Username: {username}\n"
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
            if status == "approved":
                database.update_user_info(user_id, is_employee=1)
                await bot.send_message(user_id, "🎉 Tabriklaymiz, siz tasdiqlandingiz!\nEndi <b>🧑‍💻 Xodimlar bo'limi</b>dan foydalanishingiz mumkin.", reply_markup=get_main_menu(user_lang, user_id))
            else:
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
            if status == "approved":
                database.update_user_info(user_id, is_employee=1)
                await bot.send_message(user_id, "🎉 Tabriklaymiz, siz tasdiqlandingiz!\nEndi <b>🧑‍💻 Xodimlar bo'limi</b>dan foydalanishingiz mumkin.", reply_markup=get_main_menu(user_lang, user_id))
            else:
                await bot.send_message(user_id, get_t(user_lang, msg_key))
        except:
            pass

# --- АДМИН ПАНЕЛ ---
@dp.message(F.text == "🔙 Бош меню")
async def admin_back(message: types.Message):
    if admin_sessions.get(message.from_user.id):
        del admin_sessions[message.from_user.id]
    lang = database.get_user_lang(message.from_user.id) or 'uz'
    await message.answer("Асосий меню", reply_markup=get_main_menu(lang, message.from_user.id))

@dp.message(F.text == "🔙 Ортга")
async def admin_submenu_back(message: types.Message):
    if admin_sessions.get(message.from_user.id):
        await message.answer("Админ панелига хуш келибсиз:", reply_markup=get_admin_menu())

@dp.message(F.text == "👥 Фойдаланувчилар")
async def admin_users(message: types.Message):
    if not admin_sessions.get(message.from_user.id):
        return
    users = database.get_all_users()
    if not users:
        await message.answer("Фойдаланувчилар йўқ.")
        return
    
    kb = []
    for u in users[:50]:
        btn = InlineKeyboardButton(text=f"{u[2]} (ID: {u[0]})", callback_data=f"user_info_{u[0]}")
        kb.append([btn])
    
    await message.answer("👥 Фойдаланувчини танланг (сўнгги 50 та):", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(lambda c: c.data.startswith('user_info_'))
async def process_user_info(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split('_')[2])
    u = database.get_user_info(user_id)
    if not u:
        return await callback_query.answer("Foydalanuvchi topilmadi!")
    
    refs = database.get_referrals(user_id)
    prods = database.get_user_products(user_id)
    
    # Handling potential schema differences
    is_emp = "Ha" if len(u) > 9 and u[9] else "Yo'q"
    
    text = f"👤 <b>Foydalanuvchi ma'lumoti:</b>\n"
    text += f"Ism: {u[2] or ''} {u[3] or ''}\n"
    text += f"Username: @{u[1] or 'Yoq'}\n"
    text += f"Tel: {u[4] or 'Yoq'}\n"
    text += f"Hudud: {u[5] or 'Yoq'}\n"
    text += f"Xodimmi: {is_emp}\n\n"
    
    text += f"👥 <b>Taklif qilgan odamlari ({len(refs)} ta):</b>\n"
    for r in refs:
        uname = f"(@{r[1]})" if r[1] else ""
        text += f"- {r[0]} {uname}\n"
        
    text += f"\n📦 <b>Qo'shgan maxsulotlari ({len(prods)} ta):</b>\n"
    for p in prods:
        text += f"- {p[0]} ({p[1]} so'm)\n"
        
    await callback_query.message.answer(text)
    await callback_query.answer()

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
        name = a[1]
        age = a[2]
        address = a[3]
        direction = a[4]
        date = a[6]
        
        text = (
            f"💼 <b>ИШГА АРИЗА</b> (ID: {a_id})\n"
            f"👤 Исм/Фамилия: {name}\n"
            f"🎂 Ёши: {age}\n"
            f"📍 Манзил: {address}\n"
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
    kb = [[KeyboardButton(text="🔙 Ортга")]]
    await message.answer("📢 Барча фойдаланувчиларга юбориш учун хабар матнини киритинг:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(AdminState.waiting_for_broadcast)

@dp.message(AdminState.waiting_for_broadcast)
async def admin_broadcast_send(message: types.Message, state: FSMContext):
    if message.text == '🔙 Ортга' or message.text == '/start':
        await state.clear()
        await message.answer("Бекор қилинди.", reply_markup=get_admin_menu())
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
        [KeyboardButton(text="🔙 Ортга")]
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


def get_employee_menu():
    kb = [
        [KeyboardButton(text="➕ Maxsulot qo'shish"), KeyboardButton(text="🔗 Referal tizimi")],
        [KeyboardButton(text="📦 Mening maxsulotlarim"), KeyboardButton(text="🔙 Asosiy menyu")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- EMPLOYEE BOT SIDE ---
@dp.message(F.text == "🧑‍💻 Xodimlar bo'limi")
async def emp_dashboard(message: types.Message):
    if not database.get_user_is_employee(message.from_user.id):
        return
    await message.answer("Xodimlar bo'limiga xush kelibsiz!", reply_markup=get_employee_menu())

@dp.message(F.text == "🔙 Asosiy menyu")
async def emp_back_main(message: types.Message):
    lang = database.get_user_lang(message.from_user.id) or 'uz'
    await message.answer("Asosiy menyu", reply_markup=get_main_menu(lang, message.from_user.id))

@dp.message(F.text == "🔗 Referal tizimi")
async def emp_referrals(message: types.Message):
    if not database.get_user_is_employee(message.from_user.id):
        return
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    refs = database.get_referrals(message.from_user.id)
    text = f"🔗 <b>Sizning referal havolangiz:</b>\n{ref_link}\n\n"
    text += f"👥 <b>Taklif qilingan a'zolar ({len(refs)} ta):</b>\n"
    for r in refs:
        name = r[0]
        uname = f"(@{r[1]}) " if r[1] else ""
        text += f"- {name} {uname}\n"
    if not refs:
        text += "Hali hech kim taklif qilinmagan."
    await message.answer(text, disable_web_page_preview=True)

@dp.message(F.text == "📦 Mening maxsulotlarim")
async def emp_my_products(message: types.Message):
    if not database.get_user_is_employee(message.from_user.id):
        return
    prods = database.get_user_products(message.from_user.id)
    if not prods:
        return await message.answer("Siz hali maxsulot qo'shmagansiz.")
    text = f"📦 <b>Siz qo'shgan maxsulotlar ({len(prods)} ta):</b>\n\n"
    for p in prods:
        text += f"▪️ <b>{p[0]}</b> - {p[1]} so'm\n"
    await message.answer(text)

@dp.message(F.text == "➕ Maxsulot qo'shish")
async def emp_add_product(message: types.Message, state: FSMContext):
    if not database.get_user_is_employee(message.from_user.id):
        return
    kb = [[KeyboardButton(text="🔙 Bekor qilish")]]
    await message.answer("Maxsulot nomini kiriting:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(ProductState.waiting_for_name)

@dp.message(ProductState.waiting_for_name)
async def process_prod_name(message: types.Message, state: FSMContext):
    if message.text == "🔙 Bekor qilish":
        await state.clear()
        return await message.answer("Bekor qilindi.", reply_markup=get_employee_menu())
    await state.update_data(name=message.text)
    kb = [[KeyboardButton(text="🔙 Bekor qilish")]]
    await message.answer("Endi maxsulot rasmini yuboring:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(ProductState.waiting_for_photo)

@dp.message(ProductState.waiting_for_photo, F.photo | F.text)
async def process_prod_photo(message: types.Message, state: FSMContext):
    if message.text == "🔙 Bekor qilish":
        kb = [[KeyboardButton(text="🔙 Bekor qilish")]]
        await message.answer("Maxsulot nomini kiriting:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        return await state.set_state(ProductState.waiting_for_name)
        
    if not message.photo:
        return await message.answer("Iltimos, rasm yuboring yoki orqaga qayting.")
        
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    kb = [[KeyboardButton(text="🔙 Bekor qilish")]]
    await message.answer("Endi maxsulot narxini kiriting (faqat raqam):", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(ProductState.waiting_for_price)

@dp.message(ProductState.waiting_for_price)
async def process_prod_price(message: types.Message, state: FSMContext):
    if message.text == "🔙 Bekor qilish":
        kb = [[KeyboardButton(text="🔙 Bekor qilish")]]
        await message.answer("Endi maxsulot rasmini yuboring:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        return await state.set_state(ProductState.waiting_for_photo)
    
    data = await state.get_data()
    database.add_product(message.from_user.id, data['name'], data['photo_id'], message.text)
    await state.clear()
    await message.answer("✅ Maxsulot muvaffaqiyatli qo'shildi!", reply_markup=get_employee_menu())

async def main():
    print("Бот ишга тушди...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
