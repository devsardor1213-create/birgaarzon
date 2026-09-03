with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace get_main_menu
old_menu = """def get_main_menu(lang, telegram_id=None):
    kb = [
        [KeyboardButton(text=get_t(lang, 'btn_survey')), KeyboardButton(text=get_t(lang, 'btn_work'))],
        [KeyboardButton(text=get_t(lang, 'btn_about')), KeyboardButton(text=get_t(lang, 'btn_operator'))]
    ]"""
    
new_menu = """def get_main_menu(lang, telegram_id=None):
    kb = [
        [KeyboardButton(text=get_t(lang, 'btn_survey')), KeyboardButton(text=get_t(lang, 'btn_work'))],
        [KeyboardButton(text=get_t(lang, 'btn_products')), KeyboardButton(text=get_t(lang, 'btn_about'))],
        [KeyboardButton(text=get_t(lang, 'btn_operator'))]
    ]"""

content = content.replace(old_menu, new_menu)

# Add handler after operator_contact
old_operator = """@dp.message(lambda msg: check_text(msg.text, 'btn_operator'))
async def operator_contact(message: types.Message):
    lang = database.get_user_lang(message.from_user.id) or 'uz'
    text = get_t(lang, 'operator_text', username=config.OPERATOR_USERNAME)
    await message.answer(text, reply_markup=get_main_menu(lang, message.from_user.id))"""

new_operator = """@dp.message(lambda msg: check_text(msg.text, 'btn_operator'))
async def operator_contact(message: types.Message):
    lang = database.get_user_lang(message.from_user.id) or 'uz'
    text = get_t(lang, 'operator_text', username=config.OPERATOR_USERNAME)
    await message.answer(text, reply_markup=get_main_menu(lang, message.from_user.id))

@dp.message(lambda msg: check_text(msg.text, 'btn_products'))
async def view_all_products(message: types.Message):
    lang = database.get_user_lang(message.from_user.id) or 'uz'
    prods = database.get_all_products()
    if not prods:
        text = "🤷‍♂️ Hozircha maxsulotlar yo'q." if lang == 'uz' else "🤷‍♂️ Пока нет товаров."
        return await message.answer(text, reply_markup=get_main_menu(lang, message.from_user.id))
        
    text = f"📦 <b>Barcha maxsulotlar ({len(prods)} ta):</b>" if lang == 'uz' else f"📦 <b>Все товары ({len(prods)}):</b>"
    await message.answer(text, reply_markup=get_main_menu(lang, message.from_user.id))
    
    for p in prods:
        prod_id = p[0]
        name = p[1]
        price = p[2]
        photo_id = p[3]
        
        caption = f"▪️ <b>{name}</b>\\n💰 Narxi / Цена: {price} so'm"
        
        ikb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Saytga o'tish" if lang == 'uz' else "🌐 Перейти на сайт", url="http://demo-user.mydiller.uz")]
        ])
        
        try:
            if photo_id:
                await bot.send_photo(message.chat.id, photo=photo_id, caption=caption, reply_markup=ikb)
            else:
                await message.answer(caption, reply_markup=ikb)
        except Exception:
            await message.answer(caption, reply_markup=ikb)"""

content = content.replace(old_operator, new_operator)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Added products feature successfully!")
