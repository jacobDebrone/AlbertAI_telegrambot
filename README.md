# Telegram AI Chatbot

A feature-rich Telegram chatbot powered by Google’s Gemini AI, designed to engage users with insightful and thought-provoking conversations. This bot leverages Flask for handling webhooks, SQLite for maintaining chat history, and includes robust rate limiting and error handling to ensure a smooth user experience.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Architecture](#architecture)
- [Logging](#logging)
- [Contributing](#contributing)
- [License](#license)

## Features

- **AI-Powered Conversations:** Utilizes Google’s Gemini 1.5-flash model to generate intelligent and engaging responses.
- **Persistent Chat History:** Stores user interactions in a SQLite database for context-aware conversations.
- **Rate Limiting:** Ensures fair usage by limiting the number of requests per user.
- **Multithreading:** Handles multiple user requests concurrently for improved performance.
- **Webhook Integration:** Uses Flask to manage Telegram webhooks securely.
- **Error Handling & Logging:** Comprehensive logging for monitoring and troubleshooting.
- **Customizable AI Persona:** Configured to behave as Albert, a distinguished astrophysicist with a unique communication style.

## Prerequisites

- Python 3.7 or higher
- A Telegram account
- Telegram Bot Token
- Google Gemini API Key
- Hosting service (e.g., Heroku, AWS, etc.) to run the Flask app and expose a public URL

## Installation

1. **Clone the Repository**


2. **Create a Virtual Environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**

   Create a `.env` file in the root directory and add the following variables:

   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   GEMINI_API_KEY=your_gemini_api_key
   WEBHOOK_URL_BASE=https://your-domain.com
   PORT=5000  # Or any other port you prefer
   ```

## Configuration

The bot requires several environment variables to function correctly. Ensure you have the following variables set in your `.env` file:

- **TELEGRAM_BOT_TOKEN:** Your Telegram bot token obtained from [BotFather](https://t.me/BotFather).
- **GEMINI_API_KEY:** Your API key for Google’s Gemini AI.
- **WEBHOOK_URL_BASE:** The base URL where your Flask app is hosted (e.g., `https://your-domain.com`).
- **PORT:** The port on which the Flask app will run (default is `5000`).

Example `.env` file:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ
GEMINI_API_KEY=your_gemini_api_key
WEBHOOK_URL_BASE=https://your-domain.com
PORT=5000
```

## Usage

1. **Initialize the Database**

   The database is automatically initialized when you run the bot for the first time. It creates a `chat_history.db` SQLite database to store user interactions.

2. **Run the Bot**

   ```bash
   python your_bot_script.py
   ```

   Replace `your_bot_script.py` with the name of your Python script containing the bot code.

3. **Set Up Webhook**

   The bot automatically sets up the webhook using the `WEBHOOK_URL_BASE` and `BOT_TOKEN`. Ensure that your hosting service correctly points to the webhook URL.

4. **Interact with the Bot**

   Open Telegram, find your bot by its username, and start interacting!

## Architecture

### Main Components

- **Flask App:** Handles incoming webhook requests from Telegram.
- **Telebot:** Manages Telegram bot interactions and messaging.
- **SQLite Database:** Stores chat history for each user to maintain context.
- **Google Generative AI (Gemini):** Generates AI-powered responses based on user input and chat history.
- **Rate Limiter:** Controls the number of requests a user can make within a specific timeframe to prevent abuse.
- **Thread Pool Executor:** Manages concurrent processing of user messages.
- **Logging:** Captures errors and warnings for monitoring and debugging.

### Workflow

1. **Webhook Reception:** Telegram sends updates to the Flask webhook route.
2. **Message Queuing:** Incoming messages are placed in a thread-safe queue.
3. **Worker Threads:** Multiple worker threads process messages concurrently.
4. **Input Validation:** Validates user input for length and content.
5. **Rate Limiting:** Checks if the user has exceeded the request limit.
6. **AI Response Generation:** Fetches chat history and generates a response using Gemini AI.
7. **Response Delivery:** Sends the formatted response back to the user via Telegram.

## Logging

The bot is configured to log errors and warnings to a file named `bot_errors.log`. This helps in monitoring the bot’s performance and troubleshooting issues.

```python
logging.basicConfig(filename='bot_errors.log', level=logging.ERROR)
```

## Contributing

Contributions are welcome! Please follow these steps to contribute:

1. **Fork the Repository**

2. **Create a New Branch**

   ```bash
   git checkout -b feature/YourFeature
   ```

3. **Commit Your Changes**

   ```bash
   git commit -m "Add your feature"
   ```

4. **Push to the Branch**

   ```bash
   git push origin feature/YourFeature
   ```

5. **Open a Pull Request**

## License

This project is licensed under the [MIT License](LICENSE).

---

*Developed with ❤️ by Jacob*
