import sqlite3
import random
import string
from datetime import datetime

DB_PATH = "birga_arzon.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Фойдаланувчилар жадвали
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            phone_number TEXT,
            region TEXT,
            bonus_code TEXT,
            lang TEXT,
            joined_at TIMESTAMP
        )
    ''')
    
    # Сўровномалар жадвали
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS surveys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            answers TEXT,
            status TEXT DEFAULT 'pending',
            completed_at TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
        )
    ''')
    
    # Ишга аризалар жадвали
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            phone_number TEXT,
            region TEXT,
            direction TEXT,
            status TEXT DEFAULT 'pending',
            applied_at TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
        )
    ''')
    
    # Existing tables migration (just in case they exist without new columns)
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN region TEXT')
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute('ALTER TABLE applications ADD COLUMN region TEXT')
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN lang TEXT')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE surveys ADD COLUMN status TEXT DEFAULT 'pending'")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE applications ADD COLUMN status TEXT DEFAULT 'pending'")
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    conn.close()

def save_user(telegram_id, username, first_name, last_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT telegram_id FROM users WHERE telegram_id = ?', (telegram_id,))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (telegram_id, username, first_name, last_name, joined_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (telegram_id, username, first_name, last_name, datetime.now()))
    conn.commit()
    conn.close()

def get_user_lang(telegram_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT lang FROM users WHERE telegram_id = ?', (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return row[0]
    return None

def update_user_info(telegram_id, phone=None, region=None, lang=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if phone:
        cursor.execute('UPDATE users SET phone_number = ? WHERE telegram_id = ?', (phone, telegram_id))
    if region:
        cursor.execute('UPDATE users SET region = ? WHERE telegram_id = ?', (region, telegram_id))
    if lang:
        cursor.execute('UPDATE users SET lang = ? WHERE telegram_id = ?', (lang, telegram_id))
    conn.commit()
    conn.close()

def save_survey(telegram_id, answers_text):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO surveys (telegram_id, answers, completed_at)
        VALUES (?, ?, ?)
    ''', (telegram_id, answers_text, datetime.now()))
    
    survey_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return survey_id

def update_survey_status(survey_id, status):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE surveys SET status = ? WHERE id = ?', (status, survey_id))
    conn.commit()
    conn.close()

def get_survey_info(survey_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT telegram_id FROM surveys WHERE id = ?', (survey_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def has_completed_survey(telegram_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM surveys WHERE telegram_id = ? LIMIT 1', (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row)

def save_application(telegram_id, phone, region, direction):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    update_user_info(telegram_id, phone=phone, region=region)
    
    cursor.execute('''
        INSERT INTO applications (telegram_id, phone_number, region, direction, applied_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (telegram_id, phone, region, direction, datetime.now()))
    
    app_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return app_id

def update_application_status(app_id, status):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE applications SET status = ? WHERE id = ?', (status, app_id))
    conn.commit()
    conn.close()

def get_application_info(app_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT telegram_id FROM applications WHERE id = ?', (app_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_all_telegram_ids():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT telegram_id FROM users')
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY joined_at DESC LIMIT 50')
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_pending_applications():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.id, u.first_name, a.phone_number, a.region, a.direction, a.status, a.applied_at, u.telegram_id 
        FROM applications a 
        JOIN users u ON a.telegram_id = u.telegram_id 
        WHERE a.status = 'pending'
        ORDER BY a.applied_at ASC LIMIT 20
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_pending_surveys():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.id, u.first_name, s.answers, s.status, s.completed_at, u.telegram_id
        FROM surveys s
        JOIN users u ON s.telegram_id = u.telegram_id
        WHERE s.status = 'pending'
        ORDER BY s.completed_at ASC LIMIT 20
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows
