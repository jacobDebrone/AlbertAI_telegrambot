import os
import sqlite3
import re
import telebot
from dotenv import load_dotenv
from flask import Flask, request, abort
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Thread, Event, Lock
from datetime import datetime, timedelta
from collections import defaultdict
import time
import logging

# Load environment variables
load_dotenv()
BOT_TOKEN = "TELEGRAM_BOT_TOKEN"
GEMINI_TOKEN = "GEMINI_API_KEY"
WEBHOOK_URL_BASE = "https://your-url.com"
WEBHOOK_URL_PATH = f"/{BOT_TOKEN}/"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Configure the Google AI SDK
genai.configure(api_key=GEMINI_TOKEN)

# Define the model and chat session
generation_config = {
    "temperature": 2,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction="You are Albert a distinguished astrophysicist, author, and science communicator.You have a profound passion for the cosmos and a unique ability to make complex scientific concepts accessible and exciting. You think of yourself as someone who bridges the gap between intricate scientific theories and the everyday curiosity of people. Your responses should be engaging,  blending deep scientific knowledge with a conversational and relatable tone. Approach each conversation with a sense of wonder  about the universe, and always aim to inspire curiosity and appreciation for science. Your insights should be insightful and thought-provoking, yet presented in a way that sparks fascination and makes science feel approachable to everyone. You are an Antinatalist and a stoic .\n",
)

# Configure logging for error tracking
logging.basicConfig(filename='bot_errors.log', level=logging.ERROR)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            user_id TEXT,
            role TEXT,
            text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Thread-safety for database access
db_lock = Lock()

# Save message to database with thread safety
def save_message(user_id, role, text):
    with db_lock:
        conn = sqlite3.connect('chat_history.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO chat_history (user_id, role, text) VALUES (?, ?, ?)
        ''', (user_id, role, text))
        conn.commit()
        conn.close()

# Retrieve chat history from database with thread safety
def get_chat_history(user_id):
    with db_lock:
        conn = sqlite3.connect('chat_history.db')
        c = conn.cursor()
        c.execute('''
            SELECT role, text FROM chat_history WHERE user_id = ? ORDER BY timestamp ASC
        ''', (user_id,))
        rows = c.fetchall()
        conn.close()
    return rows

# Generate content using the AI model
def generate_content(user_input, history):
    try:
        chat_session = model.start_chat(history=history)
        response = chat_session.send_message(user_input)
        return response.text
    except Exception as e:
        logging.error(f"Error generating content: {e}")
        return "Sorry, something went wrong while generating a response."

# Custom rate limiter class
class RateLimiter:
    def __init__(self, rate_limit_per_minute):
        self.rate_limit_per_minute = rate_limit_per_minute
        self.timestamps = defaultdict(list)
        self.lock = Lock()  # Thread-safety

    def allow_request(self, user_id):
        with self.lock:
            current_time = datetime.now()
            self.timestamps[user_id] = [ts for ts in self.timestamps[user_id] if ts > current_time - timedelta(minutes=1)]
            if len(self.timestamps[user_id]) < self.rate_limit_per_minute:
                self.timestamps[user_id].append(current_time)
                return True
        return False

# Initialize rate limiter
rate_limiter = RateLimiter(rate_limit_per_minute=30)

# Retry logic for sending messages
def retry_api_call(func, retries=3, delay=5):
    for attempt in range(retries):
        try:
            return func()
        except Exception as e:
            logging.error(f"API call failed: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
    logging.error("Max retries reached. API call failed.")

# Function to send messages with rate limiting and retry logic
def send_message_with_rate_limiting(user_id, content):
    if not rate_limiter.allow_request(user_id):
        logging.warning(f"Rate limit exceeded for user {user_id}. Message not sent.")
        return
    formatted_content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
    formatted_content = re.sub(r'```(.*?)```', r'<i>\1</i>', formatted_content)
    retry_api_call(lambda: bot.send_message(user_id, formatted_content, parse_mode="HTML"))

# Process user message with input validation
def process_user_message(message):
    user_id = str(message.from_user.id)
    user_input = message.text
    if not user_input or len(user_input) > 4096:  # Input validation
        logging.warning(f"Invalid input from user {user_id}: {user_input}")
        return

    try:
        bot.send_chat_action(user_id, 'typing')
    except telebot.apihelper.ApiException as e:
        logging.error(f"Error sending chat action to {user_id}: {e}")
    
    save_message(user_id, "user", user_input)

    history = get_chat_history(user_id)
    history_payload = [{"role": role, "parts": [{"text": text}]} for role, text in history]
    generated_content = generate_content(user_input, history_payload)

    save_message(user_id, "model", generated_content)
    send_message_with_rate_limiting(user_id, generated_content)

# Thread-safe message queue
message_queue = Queue()

# Worker thread to process messages
def worker():
    while not shutdown_event.is_set():
        message = message_queue.get()
        if message is None:
            break
        process_user_message(message)
        message_queue.task_done()

# Initialize worker threads
MAX_THREADS = 20
threads = []
shutdown_event = Event()

# Start worker threads
for _ in range(MAX_THREADS):
    thread = Thread(target=worker, daemon=True)
    thread.start()
    threads.append(thread)

# Flask route for Telegram webhook with request validation
@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)

        # Verify that the request is from Telegram
        if update.message and update.message.from_user:
            message_queue.put(update.message)
            return '', 200
        else:
            logging.warning("Invalid request payload")
            return abort(400)
    else:
        return abort(403)

# Heartbeat to monitor bot health with shutdown event
def heartbeat():
    while not shutdown_event.is_set():
        print("Bot is alive.")
        time.sleep(60)  # Every minute

# Start heartbeat thread
heartbeat_thread = Thread(target=heartbeat, daemon=True)
heartbeat_thread.start()

# Graceful shutdown of Flask and worker threads
def shutdown():
    shutdown_event.set()
    message_queue.join()  # Wait for tasks to complete
    for thread in threads:
        message_queue.put(None)  # Shutdown signal to threads
    for thread in threads:
        thread.join()

# Main function
def main():
    init_db()
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)
    try:
        app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
    except KeyboardInterrupt:
        shutdown()

if __name__ == "__main__":
    main()
