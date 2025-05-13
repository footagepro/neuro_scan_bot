import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_TELEGRAM_ID"))
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL")
RAILWAY_STATIC_URL = os.getenv("RAILWAY_STATIC_URL")

logging.basicConfig(level=logging.INFO)

flask_app = Flask(__name__)
application = ApplicationBuilder().token(BOT_TOKEN).build()
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Healthcheck
@flask_app.route("/")
def home():
    return "✅ Бот запущен!"

# Webhook endpoint
@flask_app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    application.create_task(application.process_update(update))
    return "OK", 200

# Subscription check
async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.error(f"Ошибка подписки: {e}")
        return False

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await check_subscription(context, user_id):
        await update.message.reply_text("🎉 Добро пожаловать! Доступ открыт.")
    else:
        keyboard = [
            [InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/{REQUIRED_CHANNEL.strip('@')}")],
            [InlineKeyboardButton("ВК сообщество", url="https://vk.com/footagepro")]
        ]
        await update.message.reply_text(
            "🔒 Доступ только для подписчиков канала.\n✅ Бесплатно!\nПодпишитесь и снова нажмите /start.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Handle user messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_subscription(context, user_id):
        await update.message.reply_text("❗ Сначала подпишитесь на канал.")
        return

    prompt = update.message.text
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    await update.message.reply_text(response.choices[0].message.content)

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Setup webhook before start
async def setup_webhook():
    webhook_url = f"https://{RAILWAY_STATIC_URL}/webhook"
    await application.bot.set_webhook(url=webhook_url)
    logging.info(f"✅ Webhook установлен: {webhook_url}")

# Start Flask & webhook setup
if __name__ == "__main__":
    asyncio.run(setup_webhook())
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


    # ✅ Worker Telegram для обработки обновлений из update_queue
    application.run_webhook(skip_updates=True, listen="0.0.0.0", port=5000, webhook_path="/webhook")

