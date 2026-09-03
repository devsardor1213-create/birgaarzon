with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

helper_start_idx = content.find('def get_t(lang, key, **kwargs):')
states_start_idx = content.find('class SurveyState(StatesGroup):')

if helper_start_idx != -1 and states_start_idx != -1:
    before = content[:helper_start_idx]
    after = content[states_start_idx:]
    
    middle = """def get_t(lang, key, **kwargs):
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
        [KeyboardButton(text=get_t(lang, 'btn_survey')), KeyboardButton(text=get_t(lang, 'btn_work'))],
        [KeyboardButton(text=get_t(lang, 'btn_about')), KeyboardButton(text=get_t(lang, 'btn_operator'))]
    ]
    if telegram_id and database.get_user_is_employee(telegram_id):
        kb.append([KeyboardButton(text="🧑‍💻 Xodimlar bo'limi")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_menu():
    kb = [
        [KeyboardButton(text="👥 Фойдаланувчилар"), KeyboardButton(text="📝 Сўровномалар")],
        [KeyboardButton(text="💼 Ишга аризалар"), KeyboardButton(text="👥 TG Xodimlar")],
        [KeyboardButton(text="📢 Хабар юбориш"), KeyboardButton(text="⚙️ Созламалар")]
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

def get_employee_menu():
    kb = [
        [KeyboardButton(text="➕ Maxsulot qo'shish"), KeyboardButton(text="🔗 Referal tizimi")],
        [KeyboardButton(text="📦 Mening maxsulotlarim")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- ҲОЛАТЛАР (FSM) ---
class LangState(StatesGroup):
    waiting_for_lang = State()

"""
    
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(before + middle + after)
    print('Fixed!')
else:
    print('Could not find markers')
