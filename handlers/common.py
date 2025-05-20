from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from decorators import required_admin

router = Router()

@router.message(Command("start"))
async def start_handler(message: Message):
    is_admin = await required_admin()(message)

    if is_admin:
        await message.reply("Вы являетесь администратором. Введите /start_admin для списка команд.")
    else:
        await message.reply("Команды пользователя:\n/reg <username> - Зарегистрироваться\n/status <username> - Проверить статус\n/pay <username> - Оплатить подписку\n/start - Список команд.")
