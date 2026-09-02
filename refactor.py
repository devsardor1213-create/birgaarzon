import sys

with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.startswith('@dp.callback_query(lambda c: c.data.startswith("chk_emp_"))'):
        skip = True
    if skip and line.startswith('async def main():'):
        skip = False
        
    if not skip:
        new_lines.append(line)

employee_handlers = """
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
    text = f"🔗 <b>Sizning referal havolangiz:</b>\\n{ref_link}\\n\\n"
    text += f"👥 <b>Taklif qilingan a'zolar ({len(refs)} ta):</b>\\n"
    for r in refs:
        name = r[0]
        uname = f"(@{r[1]}) " if r[1] else ""
        text += f"- {name} {uname}\\n"
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
    text = f"📦 <b>Siz qo'shgan maxsulotlar ({len(prods)} ta):</b>\\n\\n"
    for p in prods:
        text += f"▪️ <b>{p[0]}</b> - {p[1]} so'm\\n"
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

@dp.message(ProductState.waiting_for_photo, F.photo)
async def process_prod_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    kb = [[KeyboardButton(text="🔙 Bekor qilish")]]
    await message.answer("Endi maxsulot narxini kiriting (faqat raqam):", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(ProductState.waiting_for_price)

@dp.message(ProductState.waiting_for_price)
async def process_prod_price(message: types.Message, state: FSMContext):
    if message.text == "🔙 Bekor qilish":
        await state.clear()
        return await message.answer("Bekor qilindi.", reply_markup=get_employee_menu())
    
    data = await state.get_data()
    database.add_product(message.from_user.id, data['name'], data['photo_id'], message.text)
    await state.clear()
    await message.answer("✅ Maxsulot muvaffaqiyatli qo'shildi!", reply_markup=get_employee_menu())

"""

final_lines = []
for line in new_lines:
    if line.startswith('async def main():'):
        final_lines.append(employee_handlers)
    final_lines.append(line)

with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(final_lines)
