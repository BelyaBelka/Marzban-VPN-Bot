from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from decorators import admin_required
from services.marzban_api import get_marzban_token, create_user_admin, delete_user_admin, admin_status, print_list_users, extension_subscription, fetch_all_user_links

router = Router()


@router.message(Command('start_admin'))
@admin_required
async def start_admin(message: Message, **kwargs):
    await message.reply(f"Команды администратора:\n/register <username> <telegram_id>\n/del <username>\n/admin_status <username>\n/list_users\n/extension <username>\n/start_admin\n/get_users_db")


@router.message(Command('register'))
@admin_required
async def cmd_register(message: Message, **kwargs):
    parts = message.text.split()
    if len(parts) != 3:
        await message.reply("Неверный формат, должно быть: /register <username> <telegram_id>")
        return

    username = parts[1]
    try:
        telegram_id = int(parts[2])
    except ValueError:
        await message.reply("❌ Ошибка! Telegram ID должен быть числом.")
        return

    try:
        result = await create_user_admin(username, telegram_id)
        await message.reply(result)
    except Exception as e:
        await message.reply(f"❌ Ошибка: {str(e)}")


@router.message(Command('del'))
@admin_required
async def del_user(message: Message, **kwargs):
    parts = message.text.split()

    if len(parts) != 2:
        await message.reply("Неверный формат, должно быть: /del <username>")
        return

    username = parts[1]
    try:
        result = await delete_user_admin(username)
        await message.reply(result)
    except Exception as e:
        await message.reply(f"❌ Ошибка: {str(e)}")


@router.message(Command('admin_status'))
@admin_required
async def cmd_status(message: Message, **kwargs):
    try:
        parts = message.text.split()

        if len(parts) != 2:
            await message.reply("Неверный формат, запрос должен выглядеть так /admin_status <username>")
            return

        username = parts[1]
        result = await admin_status(username)
        await message.reply(result)
    except Exception as e:
        await message.reply(f"❌ Ошибка: {str(e)}")


@router.message(Command('list_users'))
@admin_required
async def user_list(message: Message, **kwargs):
    try:
        parts = message.text.split()
        page = 1
        user_per_page = 30

        if len(parts) > 1:
            try:
                page = int(parts[1])
                if page < 1:
                    page = 1
            except ValueError:
                pass

        result = await print_list_users()
        await message.reply(result)
    except Exception as e:
        await message.reply(f"❌ Ошибка {str(e)}")

@router.message(Command('extension'))
@admin_required
async def extension_user(message: Message, **kwargs):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.reply("Неверный формат, запрос должен выглядеть так /extension <username>")
            return

        username = parts[1]
        result = await extension_subscription(username)
        await message.reply(result)
    except Exception as e:
        await message.reply(f"Ошибка {str(e)}")


@router.message(Command('get_users_db'))
@admin_required
async def get_user_from_db(message: Message, **kwargs):
    try:
        response = await fetch_all_user_links()
        await message.reply(response)
    except Exception as e:
        await message.reply(f"⚠️ Ошибка при получении данных: {str(e)}")

@router.message()
async def unknown_admin_command(message: Message):
    await message.reply("Команда не распознана")