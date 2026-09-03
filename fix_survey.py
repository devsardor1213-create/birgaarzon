with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Find the start of the 'else' block inside process_survey
search_str = """    else:
        answers_str = "\\n".join([f"- {k}: {v}" for k, v in answers.items()])
        await state.update_data(answers_str=answers_str)
        kb = [[KeyboardButton(text="Ha"), KeyboardButton(text="Yo'q")]]"""

# Find the end of process_work_decision
end_str = """        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(admin_id, admin_text, reply_markup=kb)
            except:
                pass"""

start_idx = content.find('    else:\n        answers_str = "\\n".join([f"- {k}: {v}"')
end_idx = content.find(end_str) + len(end_str)

if start_idx != -1 and end_idx > start_idx:
    before = content[:start_idx]
    after = content[end_idx:]
    
    middle = """    else:
        answers_str = "\\n".join([f"- {k}: {v}" for k, v in answers.items()])
        
        survey_id = database.save_survey(message.from_user.id, answers_str)
        
        data = config.get_data()
        promo_code = data.get('promo_code', 'BIRGA-ARZON')
        
        phone = "Берилмаган"
        region = "Берилмаган"
        
        username = f"@{message.from_user.username}" if message.from_user.username else "Йўқ"
        admin_text = (
            f"🆕 <b>ЯНГИ СЎРОВНОМА</b>\\n"
            f"👤 Исм: {message.from_user.first_name}\\n"
            f"🔗 Username: {username}\\n"
            f"📱 Телефон: {phone}\\n"
            f"📍 Ҳудуд: {region}\\n"
            f"🆔 Telegram ID: {message.from_user.id}\\n"
            f"🎁 Бонус код: {promo_code}\\n"
            f"📝 <b>Сўровнома жавоблари:</b>\\n{answers_str}"
        )
        
        kb = get_decision_keyboard("surv", survey_id)
        
        ikb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Guruhga qo'shilish" if lang == 'uz' else "Вступить в группу", url="https://t.me/birgaarzonn")]
        ])
        
        await message.answer(
            "✅ So'rovnomangiz adminga yuborildi. Kuting..." if lang == 'uz' else "✅ Ваша анкета отправлена админу. Ожидайте...",
            reply_markup=ikb
        )
        
        await message.answer(
            "Menyu:" if lang == 'uz' else "Меню:",
            reply_markup=get_main_menu(lang, message.from_user.id)
        )
        
        await state.clear()
        
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(admin_id, admin_text, reply_markup=kb)
            except:
                pass"""
                
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(before + middle + after)
    print("Fixed survey flow successfully!")
else:
    print(f"Could not find indices: start={start_idx}, end={end_idx}")
