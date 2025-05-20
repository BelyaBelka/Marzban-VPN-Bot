from aiogram import Router, F, Bot
import asyncio
from aiogram.types import Message
from aiogram.filters import Command
from services.marzban_api import get_marzban_token, create_user_user, status_user, generate_payment_link, check_payment_and_extend


router = Router()


@router.message(Command('start'))
async def start_user(message: Message):
    await message.reply(f"Команды пользователя:\n/reg <username> - зарегестрироваться\n/status <username> - проверить статус подписки\n/pay <username> - оплата подписки(ССЫЛКА ДОСТУПНА В ТЕЧЕНИЕ 10 МИНУТ!)\n/start - список доступных команд")


@router.message(Command('reg'))
async def register(message: Message, **data):
    try:
        telegram_id = message.from_user.id

        parts = message.text.split()
        if len(parts) != 2:
            await message.reply("Неверный формат, должно быть: /reg <username>")
            return

        username = parts[1]
        if len(username) < 5 or len(username) > 20:
            await message.reply("❌ Имя пользователя должно содержать от 5 до 20 символов")
            return

        if not all(c.isalnum() or c == '_' for c in username):
            await message.reply("❌ Имя пользователя может содержать только латинские буквы, цифры и символ подчеркивания")
            return

        result = await create_user_user(username, telegram_id)
        await message.reply(result)
    except Exception as e:
        await message.reply(f"❌ Ошибка: {str(e)}")


@router.message(Command('status'))
async def cmd_status_user(message: Message):
    try:
        telegram_id = message.from_user.id
        parts = message.text.split()
        if len(parts) != 2:
            await message.reply("Неверный формат, запрос должен выглядеть так /status <username>")
            return

        username = parts[1]
        result = await status_user(username, telegram_id)
        await message.reply(result)
    except Exception as e:
        await message.reply(f"❌ Ошибка: {str(e)}")


@router.message(Command("pay"))
async def pay(message: Message, bot: Bot):
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("Неверный формат. Используйте: /pay <username>")
        return

    username = parts[1]
    user_id = message.from_user.id

    msg, label = await generate_payment_link(username, user_id)
    await message.reply(msg)

    if not label:
        return

    async def run_payment_check():
        result = await check_payment_and_extend(username, label, user_id)
        await bot.send_message(chat_id=message.chat.id, text=result)

    asyncio.create_task(run_payment_check())