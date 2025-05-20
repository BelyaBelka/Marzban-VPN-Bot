from aiogram.types import Message
from config import ADMIN_IDS

def admin_required(func):
    async def wrapper(message: Message, *args, **kwargs):
        if message.from_user.id not in ADMIN_IDS:
            await message.reply("⛔ У вас нет доступа к этой команде.")
            return
        return await func(message, *args, **kwargs)
    return wrapper

def required_admin():
    async def wrapper(message: Message) -> bool:
        return message.from_user.id in ADMIN_IDS
    return wrapper