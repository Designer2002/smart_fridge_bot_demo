from telebot.async_telebot import AsyncTeleBot
from utils.database import read_json, write_json
from config import admin_id
from bot.markups import admin_markup, start_markup
from config import users

async def register_commands(bot: AsyncTeleBot):
    @bot.message_handler(commands=["start"])
    async def send_welcome(message):
        user_id = str(message.from_user.id)
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        username = message.from_user.username
        display_name = f"{first_name} {last_name}".strip() if last_name else first_name

        user_data = read_json(users)
        if user_id not in user_data:
            user_data[user_id] = {
                "enabled": True,
                "display_name": display_name,
                "username": username or "Без ника",
                "state": ""
            }
            write_json(users, user_data)

        if int(user_id) == int(admin_id):
            await bot.send_message(message.chat.id, "Режим админа включен", reply_markup=admin_markup)
        else:
            await bot.send_message(
                message.chat.id,
                "Добро пожаловать в Умный Холодильник!",
                reply_markup=start_markup
            )
            