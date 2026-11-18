import os
import re
import logging
from urllib.parse import urlparse

from fastapi import FastAPI, Request, HTTPException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").rstrip("/")
if not WEBHOOK_URL:
    raise RuntimeError("Set WEBHOOK_URL to your public Render URL, e.g. https://your-service.onrender.com")

tg = Application.builder().token(TOKEN).build()
api = FastAPI()
STATE = {}

ASK_NAME, ASK_LINK, ASK_PRICE = range(3)


def valid_url(value: str) -> bool:
    try:
        parsed = urlparse(value.strip())
        return parsed.scheme in ("https", "http") and bool(parsed.netloc)
    except Exception:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    STATE.pop(update.effective_user.id, None)
    await update.message.reply_text(
        "Привет! Я конструктор предложений.\n\n"
        "Нажми /create, чтобы создать карточку."
    )


async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    STATE[update.effective_user.id] = {"step": ASK_NAME}
    await update.message.reply_text("Введите название вашего бота или проекта:")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    STATE.pop(update.effective_user.id, None)
    await update.message.reply_text("Создание отменено. Чтобы начать заново: /create")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    data = STATE.get(uid)
    if not data:
        await update.message.reply_text("Чтобы создать карточку, используйте /create.")
        return

    value = (update.message.text or "").strip()
    if data["step"] == ASK_NAME:
        if not value or len(value) > 64:
            await update.message.reply_text("Название должно быть от 1 до 64 символов. Попробуйте ещё раз:")
            return
        data["name"] = value
        data["step"] = ASK_LINK
        await update.message.reply_text("Теперь отправьте ссылку на подарок (http или https):")
        return

    if data["step"] == ASK_LINK:
        if not valid_url(value):
            await update.message.reply_text("Похоже, это не ссылка. Отправьте полный адрес, начинающийся с https://")
            return
        data["link"] = value
        data["step"] = ASK_PRICE
        await update.message.reply_text("Укажите цену в Telegram Stars (только целое число):")
        return

    if data["step"] == ASK_PRICE:
        if not re.fullmatch(r"\d{1,9}", value) or int(value) < 1:
            await update.message.reply_text("Введите положительное целое число, например 1200:")
            return
        data["price"] = int(value)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Открыть ссылку на подарок", url=data["link"])],
            [InlineKeyboardButton("Создать ещё", callback_data="again")]
        ])
        text = (
            f"✨ Предложение от: {data['name']}\\n\\n"
            f"🎁 Подарок: {data['link']}\\n"
            f"⭐ Цена: {data['price']:,} Stars\\n\\n"
            "Карточка создана вашим ботом. Цена указана автором предложения; "
            "это не подтверждение оплаты или передачи подарка."
        ).replace(",", " ")
        await update.message.reply_text(text, reply_markup=keyboard, disable_web_page_preview=False)
        STATE.pop(uid, None)


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "again":
        STATE[query.from_user.id] = {"step": ASK_NAME}
        await query.message.reply_text("Введите название вашего бота или проекта:")


tg.add_handler(CommandHandler("start", start))
tg.add_handler(CommandHandler("create", create))
tg.add_handler(CommandHandler("cancel", cancel))
tg.add_handler(CallbackQueryHandler(callbacks))
tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))


@api.on_event("startup")
async def startup():
    await tg.initialize()
    await tg.start()
    await tg.bot.set_webhook(f"{WEBHOOK_URL}/telegram/webhook")


@api.on_event("shutdown")
async def shutdown():
    await tg.bot.delete_webhook()
    await tg.stop()
    await tg.shutdown()


@api.get("/")
async def health():
    return {"status": "ok", "service": "offer-builder-bot"}


@api.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    try:
        payload = await request.json()
        update = Update.de_json(payload, tg.bot)
        await tg.process_update(update)
        return {"ok": True}
    except Exception as exc:
        log.exception("Webhook processing failed")
        raise HTTPException(status_code=500, detail="Webhook processing failed") from exc
