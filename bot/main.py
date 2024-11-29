import asyncio
from telebot.async_telebot import AsyncTeleBot
from commands import register_commands
from message_handler import handle_messages
from callbacks import handle_callbacks
from utils.data_loaders import config_data

bot = AsyncTeleBot(config_data['bot_token'])


 
async def main():
    from event_handlers import shutdown_stream
    from utils.scheduler import run_scheduler
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
    finally:
        shutdown_stream.on_next(True)  # Завершаем поток

if __name__ == "__main__":
    asyncio.run(main())