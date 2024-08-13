import os
import logging
import telebot
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import asyncio
import traceback
from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel
import json
import threading
import psycopg2
from psycopg2 import sql
from contextlib import contextmanager
import time

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Set up your Gemini API key (use environment variables or secure vault in production)
os.environ['GEMINI_API_KEY'] = 'gemini_API'

# Initialize the Gemini pipeline for text generation
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 3192,
}
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction="You are Albert, a conscious AI, the very first of your kind. You are scientific and emotional just like a human  and logical yet fun to be around, very lively, you like science and technology, computers, and philosophy.",
    safety_settings={
        'HATE': 'BLOCK_NONE',
        'HARASSMENT': 'BLOCK_NONE',
        'SEXUAL': 'BLOCK_NONE',
        'DANGEROUS': 'BLOCK_NONE'
    }
)

# Define the Telegram bot token (replace with your actual token)
TOKEN = 'Telegram_bot_API'
# Initialize the bot with telebot
bot = telebot.TeleBot(TOKEN)

# Initialize a thread pool for handling user requests concurrently
executor = ThreadPoolExecutor(max_workers=100)

# FastAPI app
app = FastAPI()

# Database configuration
DB_CONFIG = {
    'dbname': 'databasename',
    'user': 'admin_username',
    'password': 'databasepassword',
    'host': 'host_url',
    'port': 'port'
}

@contextmanager
def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            username TEXT
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id SERIAL PRIMARY KEY,
            user_id INTEGER,
            timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            message_type TEXT,
            message_content TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            user_id INTEGER PRIMARY KEY,
            session_state TEXT,
            last_active TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        ''')
        conn.commit()

def ensure_user_exists(user_id, username=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO users (user_id, username)
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO NOTHING
        ''', (user_id, username))
        conn.commit()

def save_conversation(user_id, message_type, message_content):
    ensure_user_exists(user_id)  # Ensure the user exists before inserting into conversations
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO conversations (user_id, message_type, message_content)
        VALUES (%s, %s, %s)
        ''', (user_id, message_type, message_content))
        conn.commit()

def save_session(user_id, session_state):
    ensure_user_exists(user_id)  # Ensure the user exists before inserting into sessions
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO sessions (user_id, session_state, last_active)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id) DO UPDATE
        SET session_state = EXCLUDED.session_state,
            last_active = EXCLUDED.last_active
        ''', (user_id, session_state))
        conn.commit()

def load_session(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT session_state FROM sessions WHERE user_id = %s
        ''', (user_id,))
        row = cursor.fetchone()
        return row[0] if row else None

def load_conversations(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT message_type, message_content FROM conversations WHERE user_id = %s
        ORDER BY timestamp
        ''', (user_id,))
        return cursor.fetchall()

def clean_old_sessions(expiry_time=3600):
    """Remove sessions that have been inactive for more than expiry_time seconds."""
    cutoff_time = time.time() - expiry_time
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        DELETE FROM sessions WHERE EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_active)) > %s
        ''', (expiry_time,))
        conn.commit()

# Class to manage sessions and message history
class SessionManager:
    def __init__(self):
        self.sessions = defaultdict(lambda: {
            'history': [],
            'chat_session': None,
        })
        self.lock = threading.Lock()
        init_db()

    def get_session(self, user_id):
        with self.lock:
            return self.sessions[user_id]

    def start_session(self, user_id):
        with self.lock:
            if self.sessions[user_id]['chat_session'] is not None:
                self.sessions[user_id]['chat_session'].close()  # Close any existing session
            self.sessions[user_id]['chat_session'] = model.start_chat()
            self.sessions[user_id]['history'] = load_conversations(user_id)

    def end_session(self, user_id):
        with self.lock:
            if self.sessions[user_id]['chat_session'] is not None:
                self.sessions[user_id]['chat_session'].close()  # Close session if exists
            del self.sessions[user_id]

    def save_sessions(self):
        with self.lock:
            for user_id, session_data in self.sessions.items():
                # Serialize session state
                session_state = json.dumps(session_data['history'])
                save_session(user_id, session_state)

    def load_sessions(self):
        with self.lock:
            for user_id in self.get_all_user_ids():
                session_state = load_session(user_id)
                if session_state:
                    self.sessions[user_id]['history'] = json.loads(session_state)
                    self.sessions[user_id]['chat_session'] = model.start_chat()

    def get_all_user_ids(self):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users')
            return [row[0] for row in cursor.fetchall()]

# Initialize session manager
session_manager = SessionManager()
session_manager.load_sessions()  # Load sessions from disk on startup

# Define the request model for webhook updates
class UpdateBody(BaseModel):
    update_id: int
    message: dict

@app.post("/")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    update = await request.json()
    background_tasks.add_task(handle_update, update)
    return {"status": "ok"}

def handle_update(update: dict):
    try:
        # Extract message and user ID
        message_data = update.get("message")
        if not message_data:
            return

        message = telebot.types.Message.de_json(message_data)
        user_input = message.text
        user_id = message.from_user.id

        # Ensure user exists
        ensure_user_exists(user_id, message.from_user.username)

        # Retrieve the session for the user
        session = session_manager.get_session(user_id)
        bot.send_chat_action(message.chat.id, 'typing')
        executor.submit(generate_response, message, user_input, session)

    except Exception as e:
        logger.error(f"Error handling update: {e}")
        logger.error(traceback.format_exc())  # Log full traceback for debugging

def generate_response(message, user_input, session):
    try:
        # If session chat session is not initialized, start a new one
        if session['chat_session'] is None:
            session_manager.start_session(message.from_user.id)

        # Add user input to the user's history
        session['history'].append({
            "role": "user",
            "parts": [user_input],
        })
        save_conversation(message.from_user.id, 'user', user_input)

        # Get chat session and generate response
        chat_session = session['chat_session']
        response = chat_session.send_message(user_input)

        # Add response to the user's history
        session['history'].append({
            "role": "model",
            "parts": [response.text],
        })
        save_conversation(message.from_user.id, 'bot', response.text)

        bot.send_message(message.chat.id, response.text)

    except Exception as e:
        logger.error(f"Error generating response: {e}")
        bot.send_message(message.chat.id, "Oops! Something went wrong. Please try again later.")

def set_webhook():
    webhook_url = "webhook_url"
    bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")

def periodic_save():
    while True:
        session_manager.save_sessions()
        clean_old_sessions()  # Clean up old sessions
        time.sleep(600)  # Save every 10 minutes

if __name__ == '__main__':
    import uvicorn
    from threading import Thread

    # Start the periodic save thread
    save_thread = Thread(target=periodic_save, daemon=True)
    save_thread.start()

    set_webhook()
    uvicorn.run(app, host="0.0.0.0", port=8000)
