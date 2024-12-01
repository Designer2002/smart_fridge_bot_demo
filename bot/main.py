import sys
sys.path.append("my_utils")


import asyncio
from telebot.async_telebot import AsyncTeleBot
from commands import register_commands
from message_handler import handle_messages
from callbacks import handle_callbacks
import my_utils.data_loaders
from event_handlers import initialize_streams

bot = AsyncTeleBot(my_utils.data_loaders.config_data["bot_token"])

initialize_streams(bot)
 
async def main():
    from my_utils.scheduler import run_scheduler
    try:
        # Регистрируем обработчики
        await register_commands(bot)
        await handle_messages(bot)
        await handle_callbacks(bot)

        print("Бот запущен.")
        run_scheduler(bot)  # Запускаем фоновый планировщик
        await bot.infinity_polling()
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())