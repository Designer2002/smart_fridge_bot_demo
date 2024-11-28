import asyncio
from telebot.async_telebot import AsyncTeleBot
from bot.commands import register_commands
from bot.message_handler import handle_messages
from bot.callbacks import handle_callbacks
from utils.scheduler import run_scheduler
from config import bot_token, shutdown_stream

bot = AsyncTeleBot(bot_token)

# Регистрируем обработчики
register_commands(bot)
handle_messages(bot)
handle_callbacks(bot)

async def main():
    try:
        print("Бот запущен.")
        run_scheduler(bot)  # Запускаем фоновый планировщик
        bot.infinity_polling()
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        shutdown_stream.on_next(True)  # Завершаем поток

if __name__ == "__main__":
    asyncio.run(main())