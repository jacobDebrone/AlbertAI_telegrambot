

#  Albert AI 

Dive into the future with our powerful Telegram bot that brings together cutting-edge Gemini AI and FastAPI. This project is designed to deliver engaging and intelligent conversations, manage user sessions, and keep everything running smoothly with PostgreSQL.

## 🚀 What This Project Does

- **🎉 Telegram Bot Magic**: Our bot chats with users, providing dynamic and thoughtful responses powered by Gemini AI.
- **🤖 Gemini AI Brilliance**: Leveraging the Gemini model to generate context-aware, lively conversations.
- **⚡ FastAPI Backend**: Manages webhooks, processes updates, and keeps everything in sync.
- **💾 PostgreSQL Power**: Stores all your user sessions and conversations securely.
- **🔄 Concurrency**: Handles multiple chats simultaneously like a pro, thanks to our ThreadPool.
- **🕒 Periodic Saving**: Keeps your data safe and clean by regularly saving sessions and removing old ones.

## 🛠️ Getting Started

Follow these steps to set up your bot and get it running in no time:

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/your-repo/telegram-bot-gen-ai.git
   cd telegram-bot-gen-ai
   ```

2. **Set Up a Virtual Environment (Recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install the Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Your Environment:**

   Set these environment variables to keep your secrets safe:
   - `GEMINI_API_KEY`: Your secret key for the Gemini API.
   - `TELEGRAM_BOT_TOKEN`: The magic token for your Telegram bot.
   - PostgreSQL connection details in `DB_CONFIG`.

   Create a `.env` file like this:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   ```


   ```

## 🏃‍♂️ Running the Application

1. **Start the Show:**
   ```bash
   python main.py
   ```

   This will:
   - Launch the FastAPI server on port 8000.
   - Set up your Telegram bot’s webhook.
   - Kick off periodic session saving.

2. **Check Your Webhook:**

   Look at the logs to ensure everything is hooked up correctly.

3. **Test FastAPI:**

   Open your browser and head to `http://localhost:8000` to confirm FastAPI is up and running.

## 🌍 Deployment Tips

Deploying to platforms like Railway, Vercel, or Heroku? Follow their guides for deploying FastAPI apps and don’t forget to set your environment variables properly in their settings.

## ⚙️ Configuration Details

- **🔍 Logging**: Logs are set to INFO level by default. Feel free to tweak as needed.
- **⚙️ Thread Pool**: Ready to handle up to 100 simultaneous requests. Adjust if you need more or less.
- **🧹 Database Cleanup**: Sessions older than an hour are automatically cleaned. Adjust the `expiry_time` in `clean_old_sessions()` if needed.

## 🐛 Troubleshooting

- **API Key Woes**: Double-check your `GEMINI_API_KEY` for correctness and permissions.
- **Bot Token Troubles**: Ensure your `TELEGRAM_BOT_TOKEN` is valid and correctly set.
- **Database Connection**: Verify your PostgreSQL connection details and ensure the server is reachable.
- **Webhook connecction** Make sure to include your webhook url in the code

## 🤝 Contributing

Got ideas or improvements? I would  love to see them! Submit issues or pull requests, and don’t forget to test and document your changes.
Dont forget to give a star 😌

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for all the details.

---
