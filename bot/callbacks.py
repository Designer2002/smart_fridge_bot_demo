import datetime
from telebot.async_telebot import AsyncTeleBot

from my_utils.database import read_json, write_json
from markups import back_skip_markup

from telebot_calendar import Calendar, CallbackData, RUSSIAN_LANGUAGE

calendar = Calendar(language=RUSSIAN_LANGUAGE)
calendar_1 = CallbackData('calendar_1', 'action', 'year', 'month', 'day')

async def handle_callbacks(bot: AsyncTeleBot):
    from helpers import SEPARATOR, start_adding_food
    import my_utils.data_loaders
    from event_handlers import products_stream

    @bot.callback_query_handler(func=lambda call: call.data.startswith("register"))
    async def register_product(call):
        try:
            print(call.data)
            # Загружаем события
            events = read_json(my_utils.data_loaders.config_data['events'])
            uuid = call.data.split(SEPARATOR)[-1]
            
            # Проверяем, существует ли продукт
            if uuid not in events:
                await bot.answer_callback_query(call.id, "Продукт больше недоступен.")
                return

            searched_state = events[uuid]

            if searched_state["state"] == "in_progress":
                await bot.answer_callback_query(call.id, "Этот продукт уже регистрирует другой пользователь.")
                return

            if searched_state["state"] == "registered":
                await bot.answer_callback_query(call.id, "Этот продукт уже зарегистрирован.")
                return

            # Обновляем статус продукта
            searched_state["state"] = "in_progress"
            events[uuid] = searched_state  # Вносим изменения обратно в общий словарь
            
            # Сохраняем изменения в JSON
            write_json(my_utils.data_loaders.config_data['events'], events)
            
            # Генерируем событие
            products_stream.on_next((uuid, "in_progress", call.message.message_id))

            users = read_json(my_utils.data_loaders.config_data['users'])
            
            id = await start_adding_food(bot, call.message, False)
            users[str(searched_state['chat_id'])]['state'] = 'waiting_for_name' + SEPARATOR + str(id)
            write_json(my_utils.data_loaders.config_data['users'], users)
            # Отправляем сообщение пользователю
            await bot.send_message(
                call.message.chat.id,
                "Вы начали регистрацию продукта. Сначала надо ввести имя продукта, который хотите зарегистрировать",
                reply_markup=None
            )
        except Exception as e:
            print(f"Ошибка: {e}")
            await bot.send_message(call.message.chat.id, "Бот не знает, что делать(((")
    

    
    @bot.callback_query_handler(func=lambda call: call.data.startswith(calendar_1.prefix))
    async def get_food_manufacture_date(call):
        try:
            uuid = call.data.split(SEPARATOR)[-1]
            events = read_json(my_utils.data_loaders.config_data['events'])
            searched = {e for e in events['id'] if e == uuid} 
            if not searched or searched["state"] != "waiting_for_manufacture_date":
                await bot.send_message(call.message.chat.id, "Ошибка: вы не в процессе добавления продукта.")
                return

            name, action, year, month, day = call.data.split(calendar_1.sep)
            
            if action == "DAY":
                chosen_date = datetime.date(int(year), int(month), int(day))
                my_utils.data_loaders.storage_tmp[searched]["manufacture_date"] = chosen_date
                write_json(my_utils.data_loaders.config_data['events'], "waiting_for_expiration_date")
                await bot.send_message(call.message.chat.id, f"Выбрана дата: {chosen_date}. Укажите срок хранения (дни) или нажмите 'Пропустить':", reply_markup=back_skip_markup)
        except Exception as e:
            print(e)

