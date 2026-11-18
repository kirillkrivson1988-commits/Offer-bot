КОНСТРУКТОР КАРТОЧЕК ПРЕДЛОЖЕНИЙ — Render Web Service

Что умеет:
- /start — приветствие
- /create — спросить название проекта, ссылку на подарок и цену в Stars
- /cancel — отменить создание
- после ввода показывает карточку в чате с кнопкой перехода по ссылке

Карточка использует нейтральное оформление от имени вашего бота и не выдаёт себя за системное сообщение Telegram.
Бот не принимает оплату и не подтверждает передачу NFT.

1) Создайте Telegram-бота через @BotFather и скопируйте токен.
2) Загрузите эти файлы в корень GitHub-репозитория.
3) Render → New → Web Service → подключите репозиторий.
4) Runtime: Python 3
5) Build Command:
   pip install -r requirements.txt
6) Start Command:
   uvicorn main:api --host 0.0.0.0 --port $PORT
7) После первого создания сервиса добавьте Environment Variables:
   BOT_TOKEN = токен от BotFather
   WEBHOOK_URL = публичный URL сервиса Render, например https://your-service.onrender.com
8) Нажмите Manual Deploy → Deploy latest commit.

После деплоя откройте своего бота в Telegram и отправьте /start, затем /create.

Важно: WEBHOOK_URL должен совпадать с URL сервиса Render. Не публикуйте BOT_TOKEN в репозитории и никому его не отправляйте.
