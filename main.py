import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "@your_channel")

logging.basicConfig(level=logging.INFO)

# ✅ Telegram Bot App
application = ApplicationBuilder().token(BOT_TOKEN).build()

# ✅ OpenAI Client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ✅ HealthCheck Flask
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "✅ Бот запущен!"

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    application.update_queue.put_nowait(update)
    return "OK", 200

# ✅ Проверка подписки
async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Ошибка проверки подписки: {e}")
        return False

# ✅ /start команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await check_subscription(context, user_id):
        await update.message.reply_text("🎉 Добро пожаловать! Вы подписаны на канал.")
    else:
        keyboard = [
            [InlineKeyboardButton("📢 Подписаться на канал", url=f"https://t.me/{REQUIRED_CHANNEL.strip('@')}")],
            [InlineKeyboardButton("Наш VK", url="https://vk.com/footagepro")]
        ]
        await update.message.reply_text(
            "🔒 Для доступа подпишитесь на наш канал.\n"
            "✅ Доступ бесплатный для подписчиков!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ✅ Обработка текстов
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_subscription(context, user_id):
        await update.message.reply_text("❗ Доступ только для подписчиков.")
        return

    prompt = update.message.text
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    await update.message.reply_text(response.choices[0].message.content)

# ✅ Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ✅ MAIN запуск
if __name__ == "__main__":
    # Установка webhook
    railway_url = os.getenv("RAILWAY_STATIC_URL")
    if railway_url:
        webhook_url = f"https://{railway_url}/webhook"
        application.bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook установлен: {webhook_url}")
    else:
        print("❗ Переменная RAILWAY_STATIC_URL не задана")

    # ✅ Параллельно запускаем Flask (healthcheck) и Telegram webhook listener
    import threading

    threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))).start()

    # ✅ Worker Telegram для обработки обновлений из update_queue
    application.run_webhook(skip_updates=True, listen="0.0.0.0", port=5000, webhook_path="/webhook")

