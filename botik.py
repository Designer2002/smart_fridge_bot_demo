import traceback
import uuid
from telebot import TeleBot, types
import json
import datetime
from telebot_calendar import Calendar, CallbackData, RUSSIAN_LANGUAGE

bot = TeleBot("YOUR_BOT_TOKEN")
calendar = Calendar(language=RUSSIAN_LANGUAGE)
calendar_1 = CallbackData('calendar_1', 'action', 'year', 'month', 'day')

# Глобальные переменные
USER_STATE = {}  # Хранит данные о состоянии пользователя
file = 'fridge_data.json'

# Клавиатуры
start_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
start_markup.add("Зарегистрировать продукт", "Проверить сроки годности")

back_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
back_markup.add("Назад")

check_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
check_markup.add("Сохранить", "Сброс")

# Функции работы с данными
def read_json():
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def write_json(data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Добавление нового продукта
def start_adding_food(message):
    product_id = str(uuid.uuid4())  # Уникальный ID
    USER_STATE[message.chat.id] = {
        "state": "waiting_for_name",
        "product": {
            "id": product_id,
            "name": "",
            "weight": 0,
            "tare_weight": 0,
            "source": "Магазин",
            "manufacture_date": None,
            "expiry_date": None,
        }
    }
    bot.send_message(message.chat.id, "Введите название продукта:", reply_markup=back_markup)

@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id, {}).get("state") == "waiting_for_name")
def get_food_name(message):
    user_data = USER_STATE[message.chat.id]
    user_data["product"]["name"] = message.text
    user_data["state"] = "waiting_for_weight"
    bot.send_message(message.chat.id, "Введите вес продукта (граммы):", reply_markup=back_markup)

@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id, {}).get("state") == "waiting_for_weight")
def get_food_weight(message):
    try:
        weight = int(message.text)
        user_data = USER_STATE[message.chat.id]
        user_data["product"]["weight"] = weight
        user_data["state"] = "waiting_for_source"
        bot.send_message(message.chat.id, "Кто приготовил продукт? (по умолчанию 'Магазин'):", reply_markup=back_markup)
    except ValueError:
        bot.send_message(message.chat.id, "Введите корректный вес в граммах.")

@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id, {}).get("state") == "waiting_for_source")
def get_food_source(message):
    user_data = USER_STATE[message.chat.id]
    user_data["product"]["source"] = message.text if message.text else "Магазин"
    user_data["state"] = "waiting_for_manufacture_date"
    bot.send_message(message.chat.id, "Выберите дату изготовления продукта на календаре:", reply_markup=calendar.create_calendar(calendar_1.prefix, datetime.datetime.now.year, datetime.datetime.now.month))

@bot.callback_query_handler(func=lambda call: call.data.startswith(calendar_1.prefix))
def get_food_manufacture_date(call):
    user_data = USER_STATE.get(call.message.chat.id)
    if not user_data or user_data["state"] != "waiting_for_manufacture_date":
        bot.send_message(call.message.chat.id, "Ошибка: вы не в процессе добавления продукта.")
        return

    name, action, year, month, day = call.data.split(calendar_1.sep)
    if action == "DAY":
        chosen_date = datetime.date(int(year), int(month), int(day))
        user_data["product"]["manufacture_date"] = chosen_date
        user_data["state"] = "waiting_for_expiration_date"
        bot.send_message(call.message.chat.id, f"Выбрана дата: {chosen_date}. Укажите срок хранения (дни):", reply_markup=back_markup)

@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id, {}).get("state") == "waiting_for_expiration_date")
def get_food_expiration_date(message):
    try:
        days = int(message.text)
        user_data = USER_STATE[message.chat.id]
        product = user_data["product"]
        product["expiry_date"] = product["manufacture_date"] + datetime.timedelta(days=days)
        user_data["state"] = "final_check"
        bot.send_message(message.chat.id, f"Проверьте данные:\nНазвание: {product['name']}\nВес: {product['weight']} г\nИсточник: {product['source']}\nДата изготовления: {product['manufacture_date']}\nГоден до: {product['expiry_date']}", reply_markup=check_markup)
    except ValueError:
        bot.send_message(message.chat.id, "Введите срок хранения в днях.")

@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id, {}).get("state") == "final_check")
def finalize_product(message):
    if message.text == "Сохранить":
        user_data = USER_STATE.pop(message.chat.id, None)
        if user_data:
            product = user_data["product"]
            data = read_json()
            data.append(product)
            write_json(data)
            bot.send_message(message.chat.id, "Продукт успешно сохранен!", reply_markup=start_markup)
    elif message.text == "Сброс":
        USER_STATE.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "Данные сброшены.", reply_markup=start_markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Добро пожаловать в Умный Холодильник!", reply_markup=start_markup)

bot.polling()
