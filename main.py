from pyrogram import Client
import asyncio
from dotenv import load_dotenv
import os

from logger import setup_logger
from config import load_config, add_existing_users_to_db
from handlers import StartHandler, HelpButton, InviteButton, EventButton, DepartureHandler, MessageHandler, NewMemberHandler, ChatSelectionHandler

# Настройка логирования
logger = setup_logger()

# Загрузка переменных окружения
load_dotenv()



# Получение значений из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PROXY_URL = os.getenv('PROXY_URL')

# Загрузка конфигурации
try:
    chats = load_config()
    INVITING_CHAT_ID = chats.get("INVITING_CHAT")
    INVITED_CHAT_ID = chats.get("INVITED_CHAT")
except Exception as e:
    logger.error(f"Ошибка загрузки конфигурации: {e}")
    INVITING_CHAT_ID = None
    INVITED_CHAT_ID = None

# Инициализация клиента Pyrogram
app = Client(
    "@Main_Sharyinets_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=TELEGRAM_BOT_TOKEN,
    proxy={"enabled": True, "hostname": PROXY_URL.split("//")[1].split(":")[0], "port": int(PROXY_URL.split(":")[-1])} if PROXY_URL else None
)

# Регистрация обработчиков
StartHandler(app)
HelpButton(app)
InviteButton(app, INVITING_CHAT_ID, INVITED_CHAT_ID)
EventButton(app, INVITED_CHAT_ID)
DepartureHandler(app, INVITED_CHAT_ID)
NewMemberHandler(app)
ChatSelectionHandler(app)
MessageHandler(app)

async def main():
    logger.info("Запуск приложения")
    if INVITING_CHAT_ID:
        try:
            await add_existing_users_to_db(app, INVITING_CHAT_ID)
        except Exception as e:
            logger.error(f"Ошибка добавления пользователей из чата INVITING_CHAT: {e}")
    if INVITED_CHAT_ID:
        try:
            await add_existing_users_to_db(app, INVITED_CHAT_ID)
        except Exception as e:
            logger.error(f"Ошибка добавления пользователей из чата INVITED_CHAT: {e}")

    async with app:
        await app.start()
        logger.info("Бот успешно запущен")
        await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"Критическая ошибка в основном потоке: {e}")