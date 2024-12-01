import datetime
from telebot.async_telebot import AsyncTeleBot

from my_utils.database import read_json, write_json, save_storage_tmp, load_storage_tmp
from markups import back_skip_markup

from telebot_calendar import Calendar, CallbackData, RUSSIAN_LANGUAGE

calendar = Calendar(language=RUSSIAN_LANGUAGE)
calendar_1 = CallbackData("calendar_1", "action", "year", "month", "day")

async def handle_callbacks(bot: AsyncTeleBot):
    from helpers import SEPARATOR, start_adding_food
    import my_utils.data_loaders
    from event_handlers import products_stream

    @bot.callback_query_handler(func=lambda call: call.data.startswith("register"))
    async def register_product(call):
        try:
            print(call.data)
            # Загружаем события
            events = read_json(my_utils.data_loaders.config_data["events"])
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
            write_json(my_utils.data_loaders.config_data["events"], events)
            
            # Генерируем событие
            products_stream.on_next((uuid, "in_progress", call.message.message_id))

            users = read_json(my_utils.data_loaders.config_data["users"])
            
            await start_adding_food(bot, call, False)
            users[str(searched_state["chat_id"])]["state"] = "waiting_for_name" + SEPARATOR + str(uuid)
            write_json(my_utils.data_loaders.config_data["users"], users)
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
        from my_utils.data_loaders import config_data
        try:
            
            s = load_storage_tmp()
            u = read_json(config_data['users'])
            uuid = u[str(call.message.chat.id)]['state'].split(SEPARATOR)[-1]
            searched = u[str(call.message.chat.id)]
            if not searched or not searched["state"].startswith("waiting_for_manufacture_date"):
                await bot.send_message(call.message.chat.id, "Ошибка: вы не в процессе добавления продукта.")
                return

            name, action, year, month, day = call.data.split(calendar_1.sep)
            
            if action == "DAY":
                chosen_date = datetime.date(int(year), int(month), int(day))
                s = load_storage_tmp()
                u[str(call.message.chat.id)]["state"] = "waiting_for_expiration_date"+SEPARATOR+uuid
                s[str(uuid)]["manufacture_date"] = chosen_date.isoformat()
                save_storage_tmp(s)
                write_json(config_data['users'],u)
                await bot.send_message(call.message.chat.id, f"Выбрана дата: {chosen_date}. Укажите срок хранения (дни) или нажмите 'Пропустить':", reply_markup=back_skip_markup)
        except Exception as e:
            print(e)

