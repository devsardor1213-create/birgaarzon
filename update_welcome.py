import json

with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

uz_text = """👋 Assalomu alaykum, <b>{name}</b>! BIRGA ARZON botiga xush kelibsiz! 🛒

🤝 BIRGA ARZON — mahsulotlarni birgalikda buyurtma qilib, arzonroq narxda xarid qilish imkonini beruvchi loyiha.

🎁 Bot orqali siz:
✅ Qisqa so'rovnomada ishtirok etasiz
✅ O'z oilangiz ehtiyojlarini belgilaysiz
✅ Arzon narxdagi takliflardan xabardor bo'lasiz
✅ Birinchi xarid uchun bonus-kod olishingiz mumkin

📋 Quyidagi menyudan kerakli bo'limni tanlang.
🚀 BIRGA ARZON — birga olsak, arzon!"""

ru_text = """👋 Здравствуйте, <b>{name}</b>! Добро пожаловать в бот BIRGA ARZON! 🛒

🤝 BIRGA ARZON — это проект, позволяющий совместно заказывать продукты и покупать их по более низким ценам.

🎁 Через бот вы:
✅ Участвуете в коротком опросе
✅ Определяете потребности своей семьи
✅ Узнаете о выгодных предложениях
✅ Можете получить бонус-код на первую покупку

📋 Выберите нужный раздел из меню ниже.
🚀 BIRGA ARZON — вместе дешевле!"""

data["texts"]["uz"]["welcome"] = uz_text
data["texts"]["ru"]["welcome"] = ru_text

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
