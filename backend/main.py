from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3
import re
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'data' / 'assistant.db'
FRONTEND_DIR = BASE_DIR / 'frontend'
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title='Mia Voice Command AI', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

DEFAULT_COMMANDS = [
    ('google', 'open google', 'https://www.google.com', 'Open Google in the browser.'),
    ('youtube', 'open youtube', 'https://www.youtube.com', 'Open YouTube in the browser.'),
    ('gmail', 'open gmail', 'https://mail.google.com', 'Open Gmail in the browser.'),
    ('chatgpt', 'open chatgpt', 'https://chatgpt.com', 'Open ChatGPT in the browser.'),
    ('facebook', 'open facebook', 'https://www.facebook.com', 'Open Facebook in the browser.'),
    ('instagram', 'open instagram', 'https://www.instagram.com', 'Open Instagram in the browser.'),
    ('whatsapp', 'open whatsapp', 'https://web.whatsapp.com', 'Open WhatsApp Web in the browser.'),
    ('github', 'open github', 'https://github.com', 'Open GitHub in the browser.'),
    ('stackoverflow', 'open stackoverflow', 'https://stackoverflow.com', 'Open Stack Overflow in the browser.'),
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            trigger_text TEXT NOT NULL,
            url TEXT NOT NULL,
            description TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS command_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_text TEXT NOT NULL,
            response TEXT NOT NULL,
            command_name TEXT,
            url TEXT,
            success INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )''')
        for item in DEFAULT_COMMANDS:
            conn.execute('''INSERT OR IGNORE INTO commands(name, trigger_text, url, description)
                            VALUES (?, ?, ?, ?)''', item)
        conn.commit()


class CommandRequest(BaseModel):
    text: str
    open_browser: bool = False


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return re.sub(r'\s+', ' ', text)


def strip_wake_word(text: str) -> str:
    value = normalize(text)
    for wake in ('hey Mia', 'hey razor', 'Mia', 'razor', 'hey assistant'):
        if value.startswith(wake):
            return value[len(wake):].strip()
    return value


def find_command(text: str):
    normalized = strip_wake_word(text)
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM commands ORDER BY LENGTH(trigger_text) DESC').fetchall()
    for row in rows:
        name = normalize(row['name'])
        trigger = normalize(row['trigger_text'])
        if name in normalized or trigger in normalized:
            return row
        if f'open {name}' in normalized or f'go to {name}' in normalized or f'navigate to {name}' in normalized:
            return row
    return None


def save_history(user_text, response, command_name=None, url=None, success=True):
    with get_db() as conn:
        conn.execute('''INSERT INTO command_history
            (user_text, response, command_name, url, success, created_at)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (user_text, response, command_name, url, 1 if success else 0,
             datetime.now().isoformat(timespec='seconds')))
        conn.commit()


@app.on_event('startup')
def startup():
    init_db()


@app.get('/api/health')
def health():
    return {'status': 'ok', 'assistant': 'Mia Assistant'}


@app.get('/api/commands')
def commands():
    with get_db() as conn:
        rows = conn.execute('SELECT id, name, trigger_text, url, description FROM commands ORDER BY name').fetchall()
    return [dict(row) for row in rows]


@app.get('/api/history')
def history(limit: int = 30):
    limit = max(1, min(limit, 100))
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM command_history ORDER BY id DESC LIMIT ?', (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


@app.post('/api/command')
def process_command(payload: CommandRequest):
    raw = payload.text.strip()
    if not raw:
        raise HTTPException(status_code=400, detail='Command text is required.')

    normalized = strip_wake_word(raw)
    if normalized in {'stop', 'exit', 'quit', 'shutdown', 'bye', 'goodbye', 'close'}:
        response = 'Okay, I will stop listening.'
        save_history(raw, response, success=True)
        return {'success': True, 'response': response, 'action': 'stop', 'url': None, 'command': None}

    row = find_command(raw)
    if row:
        response = f"Okay, I will open {row['name'].title()}."
        # Browser opening is optional. Frontend normally opens the returned URL so it works in a browser UI.
        if payload.open_browser:
            try:
                webbrowser.open(row['url'], new=2)
            except Exception:
                pass
        save_history(raw, response, row['name'], row['url'], True)
        return {
            'success': True,
            'response': response,
            'action': 'open_url',
            'url': row['url'],
            'command': dict(row),
        }

    response = "Sorry, I don't know that command yet. Try saying 'open YouTube' or 'open Google'."
    save_history(raw, response, success=False)
    return {'success': False, 'response': response, 'action': 'unknown', 'url': None, 'command': None}


@app.post('/api/commands')
def add_command(payload: dict):
    name = normalize(str(payload.get('name', '')))
    trigger = normalize(str(payload.get('trigger_text', '')))
    url = str(payload.get('url', '')).strip()
    description = str(payload.get('description', '')).strip()
    if not name or not trigger or not url.startswith(('http://', 'https://')):
        raise HTTPException(status_code=400, detail='name, trigger_text and a valid http(s) URL are required.')
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO commands(name, trigger_text, url, description) VALUES (?, ?, ?, ?)',
                         (name, trigger, url, description))
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail='A command with that name already exists.')
    return {'success': True, 'message': 'Command added.'}


app.mount('/', StaticFiles(directory=FRONTEND_DIR, html=True), name='frontend')
