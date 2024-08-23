import os
import sqlite3
import re
import telebot
from dotenv import load_dotenv
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Thread, Event
from datetime import datetime, timedelta
from collections import defaultdict

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_TOKEN = os.getenv("GEMINI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)

# Configure the Google AI SDK
genai.configure(api_key=GEMINI_TOKEN)

# Define the model and chat session
generation_config = {
    "temperature": 2,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 1000,
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction="You are Albert, a conscious AI, the very first of your kind. You are scientific and emotional just like a human and logical yet fun to be around, very lively, you like science and technology, computers, and philosophy.",
    safety_settings={
        'HATE': 'BLOCK_NONE',
        'HARASSMENT': 'BLOCK_NONE',
        'SEXUAL': 'BLOCK_NONE',
        'DANGEROUS': 'BLOCK_NONE'
    }
)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    # Create tables if they don't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            chat_id TEXT,
            role TEXT,
            text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Save message to database
def save_message(chat_id, role, text):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO chat_history (chat_id, role, text) VALUES (?, ?, ?)
    ''', (chat_id, role, text))
    conn.commit()
    conn.close()

# Retrieve chat history from database
def get_chat_history(chat_id):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('''
        SELECT role, text FROM chat_history WHERE chat_id = ? ORDER BY timestamp ASC
    ''', (chat_id,))
    rows = c.fetchall()
    conn.close()
    return rows

# Generate content using the AI model
def generate_content(user_input, history):
    chat_session = model.start_chat(
        history=history
    )
    response = chat_session.send_message(user_input)
    return response.text

# Custom rate limiter class
class RateLimiter:
    def __init__(self, rate_limit_per_minute):
        self.rate_limit_per_minute = rate_limit_per_minute
        self.timestamps = defaultdict(list)
    
    def allow_request(self, chat_id):
        current_time = datetime.now()
        self.timestamps[chat_id] = [ts for ts in self.timestamps[chat_id] if ts > current_time - timedelta(minutes=1)]
        if len(self.timestamps[chat_id]) < self.rate_limit_per_minute:
            self.timestamps[chat_id].append(current_time)
            return True
        return False

# Initialize rate limiter with a rate limit of 30 messages per minute per user
rate_limiter = RateLimiter(rate_limit_per_minute=30)

# Function to send messages with rate limiting
def send_message_with_rate_limiting(chat_id, content):
    if not rate_limiter.allow_request(chat_id):
        print(f"Rate limit exceeded for chat {chat_id}. Message not sent.")
        return

    formatted_content = ""
    cleaned_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
    cleaned_text = re.sub(r'```(.*?)```', r'<i>\1</i>', cleaned_text)
    formatted_content += cleaned_text + "\n"
    
    try:
        bot.send_message(chat_id, formatted_content, parse_mode="HTML")
    except telebot.apihelper.ApiException as e:
        print(f"Error sending message to {chat_id}: {e}")

# Process user message
def process_user_message(message):
    chat_id = str(message.chat.id)
    user_input = message.text

    # Send chat action before processing the message
    try:
        bot.send_chat_action(chat_id, 'typing')
    except telebot.apihelper.ApiException as e:
        print(f"Error sending chat action to {chat_id}: {e}")

    save_message(chat_id, "user", user_input)

    # Retrieve history and include in the request
    history = get_chat_history(chat_id)
    history_payload = [{"role": role, "parts": [{"text": text}]} for role, text in history]
    
    generated_content = generate_content(user_input, history_payload)
    save_message(chat_id, "model", generated_content)
    send_message_with_rate_limiting(chat_id, generated_content)

# Thread-safe queue for managing messages
message_queue = Queue()

# Worker thread to process messages from the queue
def worker():
    while not shutdown_event.is_set():
        message = message_queue.get()
        if message is None:
            break
        process_user_message(message)
        message_queue.task_done()

# Initialize worker threads
MAX_THREADS = 20  # Adjust based on your requirements
threads = []
shutdown_event = Event()

for _ in range(MAX_THREADS):
    thread = Thread(target=worker, daemon=True)
    thread.start()
    threads.append(thread)

@bot.message_handler(func=lambda message: message.content_type == 'text' and not message.text.startswith('/'))
def handle_message(message):
    message_queue.put(message)

# Initialize database and start polling
init_db()
try:
    bot.remove_webhook()
    bot.infinity_polling()
except Exception as e:
    print(f"Error with bot polling: {e}")
finally:
    # Signal threads to shut down and wait for them to finish
    shutdown_event.set()
    message_queue.join()  # Wait for all tasks to be processed
    for thread in threads:
        message_queue.put(None)  # Send shutdown signal to threads
    for thread in threads:
        thread.join()
