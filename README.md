
import os
import logging
from html import escape
from urllib.parse import urlparse

from fastapi import FastAPI, Request, HTTPException
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"].rstrip("/")

PROJECT, GIFT, PRICE = range(3)

bot = Application.builder().token(TOKEN).build()
api = FastAPI()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Я помогу создать карточку предложения.\n"
        "Для начала отправь название проекта или бота:"
    )
    return PROJECT


async def get_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["project"] = update.message.text.strip()
    await update.message.reply_text(
        "🔗 Теперь отправь ссылку на Telegram-подарок:"
    )
    return GIFT


async def get_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    parsed = urlparse(link)

    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        await update.message.reply_text(
            "❌ Отправь корректную ссылку, начинающуюся с https://"
        )
        return GIFT

    context.user_data["gift"] = link
    await update.message.reply_text(
        "⭐ Введи цену предложения в Stars (только число):"
    )
    return PRICE


async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()

    if not raw.isdigit() or int(raw) <= 0:
        await update.message.reply_text(
            "❌ Введи положительное целое число."
        )
        return PRICE

    price = int(raw)
    project = escape(context.user_data["project"])
    gift = context.user_data["gift"]

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Открыть подарок", url=gift)]
    ])

    message = (
        "🎁 <b>ПРЕДЛОЖЕНИЕ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏷 <b>Проект:</b> {project}\n"
        f"⭐ <b>Цена:</b> {price:,} Stars\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔹 <i>Карточка создана ботом</i>\n"
        "🔹 <i>Не является системным уведомлением Telegram</i>"
    ).replace(",", " ")

    await update.message.reply_text(
        message,
        parse_mode="HTML",
        reply_markup=keyboard,
        disable_web_page_preview=False,
    )

    await update.message.reply_text(
        "✅ Карточка готова!\n"
        "Создать ещё одну — /create"
    )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Создание отменено. /create — начать снова.")
    return ConversationHandler.END


conversation = ConversationHandler(
    entry_points=[
        CommandHandler("start", start),
        CommandHandler("create", start),
    ],
    states={
        PROJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_project)],
        GIFT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gift)],
        PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

bot.add_handler(conversation)


@api.on_event("startup")
async def startup():
    await bot.initialize()
    await bot.start()
    await bot.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        allowed_updates=Update.ALL_TYPES,
    )


@api.on_event("shutdown")
async def shutdown():
    await bot.bot.delete_webhook()
    await bot.stop()
    await bot.shutdown()


@api.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot.bot)
    await bot.process_update(update)
    return {"ok": True}


@api.get("/")
async def home():
    return {"status": "Bot is running"}
