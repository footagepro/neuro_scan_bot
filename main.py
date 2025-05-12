from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running!"

import os
import logging
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_TELEGRAM_ID"))
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL")

app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "✅ Бот работает!"

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subscribed = await check_subscription(context, user_id)

    if subscribed:
        await update.message.reply_text(
            "🎉 Добро пожаловать! У вас есть доступ к боту."
        )
    else:
        keyboard = [[
            InlineKeyboardButton("📢 Подписаться на канал", url=f"https://t.me/{REQUIRED_CHANNEL.strip('@')}"),
            InlineKeyboardButton("ВСТУПАЙ В СООБЩЕСТВО ВК", url="https://vk.com/footagepro")
        ]]
        await update.message.reply_text(
            "🔒 Для использования бота подпишись на наш канал.\n"
            "После подписки введи команду /start заново.\n\n"
            "✅ Доступ бесплатный для подписчиков!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subscribed = await check_subscription(context, user_id)

    if not subscribed:
        await update.message.reply_text(
            "🔒 У вас нет доступа. Подпишись на канал и попробуй снова."
        )
        return

    await update.message.reply_text("Ваш запрос получен.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    import threading
    threading.Thread(target=lambda: app_web.run(host="0.0.0.0", port=8080)).start()

    app.run_polling()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
