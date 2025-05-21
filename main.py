import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers.admin import router as admin_router
from handlers.user import router as user_router
from handlers.common import router as common_router
from db import initialize_db


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация базы данных
initialize_db()


dp.include_router(common_router)
dp.include_router(user_router)
dp.include_router(admin_router)

async def main():
    # Удаление предыдущих обработчиков
    await bot.delete_webhook(drop_pending_updates=True)

    logging.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
    except Exception as e:
        logging.error(f"Ошибка при запуске: {e}")
