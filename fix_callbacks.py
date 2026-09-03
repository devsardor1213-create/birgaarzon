with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    new_lines.append(line)
    if line.startswith('async def process_survey_decision(callback_query: types.CallbackQuery):'):
        new_lines.append('    await callback_query.answer()\n')
    elif line.startswith('async def process_app_decision(callback_query: types.CallbackQuery):'):
        new_lines.append('    await callback_query.answer()\n')
    elif line.startswith('async def process_settings_soon(callback_query: types.CallbackQuery):'):
        new_lines.append('    await callback_query.answer("Tez orada...", show_alert=True)\n')

with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Added missing answers!')
