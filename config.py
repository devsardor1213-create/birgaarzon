import json

BOT_TOKEN = "8995262442:AAHqGlZAq0A1Wm_IEe5eIPHjYL7C5IMcLTQ"
ADMIN_ID = 8733326327
OPERATOR_USERNAME = "@workmydiler"

DATA_FILE = "data.json"

def get_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {DATA_FILE}: {e}")
        return {"promo_code": "", "texts": {"uz": {}, "ru": {}}, "questions": {"uz": [], "ru": []}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
