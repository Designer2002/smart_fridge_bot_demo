import datetime
from telebot.async_telebot import AsyncTeleBot
from utils.database import read_json, write_json
from markups import back_skip_markup

from telebot_calendar import Calendar, CallbackData, RUSSIAN_LANGUAGE

calendar = Calendar(language=RUSSIAN_LANGUAGE)
calendar_1 = CallbackData('calendar_1', 'action', 'year', 'month', 'day')

async def handle_callbacks(bot: AsyncTeleBot):
    from data_loaders import config_data
    from event_handlers import products_stream
    @bot.callback_query_handler(func=lambda call: call.data.startswith("register:"))
    async def register_product(call):
        try:
            product_id = call.data.split(":")[1]
            product = read_json(config_data['new_products']).get(product_id)

            if not product:
                bot.answer_callback_query(call.id, "Продукт больше недоступен.")
                return

            if product["status"] == "in_progress":
                bot.answer_callback_query(call.id, "Этот продукт уже регистрирует другой пользователь.")
                return

            if product["status"] == "registered":
                bot.answer_callback_query(call.id, "Этот продукт уже зарегистрирован.")
                return

            # Обновление статуса и отправка события
            product["status"] = "in_progress"
            product["user_id"] = call.from_user.id
            write_json(config_data['new_products'], product)
            products_stream.on_next((product_id, "in_progress"))

            await bot.answer_callback_query(call.id)
            user = read_json(config_data['users'])
            user[call.message.chat.id]['state'] = "adding_food"
            write_json(config_data['users'], user)
            await bot.send_message(call.message.chat.id, "Вы начали регистрацию продукта. Сначала надо ввести имя продукта, который хотите зарегистрировать")
        except Exception as e:
            print(e)
            await bot.send_message(call.message.chat.id, "Бот не знает, что делать(((")
    
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith(calendar_1.prefix))
    def get_food_manufacture_date(call):
        user_data = read_json(config_data['users']).get(call.message.chat.id)
        if not user_data or user_data["state"] != "waiting_for_manufacture_date":
            bot.send_message(call.message.chat.id, "Ошибка: вы не в процессе добавления продукта.")
            return

        name, action, year, month, day = call.data.split(calendar_1.sep)
        if action == "DAY":
            chosen_date = datetime.date(int(year), int(month), int(day))
            user_data["product"]["manufacture_date"] = chosen_date
            user_data["state"] = "waiting_for_expiration_date"
            bot.send_message(call.message.chat.id, f"Выбрана дата: {chosen_date}. Укажите срок хранения (дни) или нажмите 'Пропустить':", reply_markup=back_skip_markup)


