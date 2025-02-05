import datetime
import traceback
from telebot.async_telebot import AsyncTeleBot

from  database import read_json, write_json, save_storage_tmp, load_storage_tmp, read_json_array_fridge
from markups import back_skip_markup
from  data_loaders import config_data

from telebot_calendar import Calendar, CallbackData, RUSSIAN_LANGUAGE

calendar = Calendar(language=RUSSIAN_LANGUAGE)
calendar_1 = CallbackData("calendar_1", "action", "year", "month", "day")

async def handle_callbacks(bot: AsyncTeleBot):
    from helpers import SEPARATOR, start_adding_food
    import  data_loaders
    from event_handlers import products_stream

    @bot.callback_query_handler(func=lambda call: call.data.startswith("register"))
    async def register_product(call):
        try:
            print(call.data)
            # Загружаем события
            events = read_json( data_loaders.config_data["events"])
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
            searched_state["chat_id"] = call.message.chat.id
            events[uuid] = searched_state  # Вносим изменения обратно в общий словарь
           
            # Сохраняем изменения в JSON
            write_json( data_loaders.config_data["events"], events)
            
            # Генерируем событие
            products_stream.on_next((uuid, "in_progress", call.message.message_id))

            users = read_json( data_loaders.config_data["users"])
            
            await start_adding_food(bot, call, False)
            users[str(searched_state["chat_id"])]["state"] = "waiting_for_name" + SEPARATOR + str(uuid)
            write_json( data_loaders.config_data["users"], users)
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
        from  data_loaders import config_data
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
            traceback.print_exc()
            if u[str(call.message.chat.id)] is None:
                await bot.send_message(call.message.chat.id, "Вас нет в списке пользователей. Нажмите /start")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("eat"))
    async def choose_product(call):
        from markups import start_markup, eat_markup
        from data_loaders import eating_products
        if call.message.text == "Назад":
            user_data = read_json(config_data['users'])
            user_data[str(call.message_chat.id)]['state'] = 'start'
            write_json(config_data['users'], user_data)
            await bot.send_message(call.message.chat.id, "Вы вернулись в главное меню.", reply_markup=start_markup)
            return

        product_name = call.data.split("_")[-1]
        if product_name in eating_products:
            await bot.send_message(call.message.chat.id, f"Продукт {product_name} уже ест другой пользователь.")
            return
        data = read_json_array_fridge(config_data['fridge'])
        data = [p for p in data if p["name"] == product_name]
        if data is None:
            await bot.send_message(call.message.chat.id, f"Продукт {product_name} уже съеден! Съешьте что-то ещё.")
            return
        # Занимаем продукт
        eating_products[product_name] = call.message.chat.id

        # Показываем варианты съедения

        await bot.send_message(
            call.message.chat.id,
            f"Вы выбрали {product_name}. Как его будете есть?",
            reply_markup=eat_markup,
        )
    @bot.callback_query_handler(func=lambda call: call.data.startswith("go_back"))
    async def choose_product(call):
        from markups import start_markup
        user_data = read_json(config_data['users'])
        user_data[str(call.message.chat.id)]['state'] = 'start'
        write_json(config_data['users'], user_data)
        await bot.send_message(call.message.chat.id, "Вы вернулись в главное меню.", reply_markup=start_markup)
        return
