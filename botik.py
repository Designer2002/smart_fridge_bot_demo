from rx import create, operators as ops
from rx.subject import Subject
import random
import re
import uuid
from telebot import TeleBot, types
import json
import datetime
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from nltk.stem.snowball import RussianStemmer
from telebot_calendar import Calendar, CallbackData, RUSSIAN_LANGUAGE

admin_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
admin_markup.add("Сообщение от датчика веса", "Рандомный продукт")
admin_id = '699861867'


bot = TeleBot("7223871421:AAG2IKwKcGALr5UUYbs15LI9ndd8xpS1FpQ")
calendar = Calendar(language=RUSSIAN_LANGUAGE)
calendar_1 = CallbackData('calendar_1', 'action', 'year', 'month', 'day')

# Глобальные переменные
USER_STATE = {}  # Хранит данные о состоянии пользователя


products_stream = Subject()

new_products = "new_products.json"
fridge = 'fridge_data.json'
users = "users.json"

# Клавиатуры
start_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
start_markup.add("Новый продукт", "Найди просрочку", "Посоветуй вкусняшку", "Удалить продукт")

drop_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
drop_markup.add("1", "3", "5", "10", "15", "20")


back_skip_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
back_skip_markup.add("Назад", "Пропустить")

check_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
check_markup.add("Сохранить", "Сброс")

CATEGORY_EMOJIS = {
    "овощ": "🥦",    # Овощи
    "молоч": "🥛",   # Молочные продукты (поиск по подстроке "молоч")
    "мясо": "🍖",     # Мясо
    "рыба": "🐟",     # Рыба
    "фрукт": "🍎",   # Фрукты
    "выпечка": "🥐",  # Выпечка
    "хлеб": "🥐",  # Выпечка
    "прочее": "🍽️"   # Прочее
}

CATEGORY_PATTERNS = {
    "овощ": r'\bовощ(и|ной|ная|ное|ные|)\b',    # Овощи
    "молоч": r'\bмолоч(ный|ные|ное|)\b',            # Молочные продукты
    "мясо": r'\bмяс(о|ные|ной|ное|)\b',             # Мясо
    "рыба": r'\bрыб(а|ы|ное|ные|)\b',               # Рыба
    "фрукт": r'\bфрукт(овый|ы|)\b',             # Фрукты
    "выпечка": r'\bвыпеч(ка|ки|ные|)\b',        # Выпечка
    "хлеб": r'\bхлеб(ный|ные|ное|ная|)\b',          # Хлеб
}

def write_json(file, data):
    try:
        # Преобразуем все даты в строки формата ISO
        for product in data:
            if isinstance(product.get("manufacture_date"), datetime.date):
                product["manufacture_date"] = product["manufacture_date"].isoformat()
            if isinstance(product.get("expiry_date"), datetime.date):
                product["expiry_date"] = product["expiry_date"].isoformat()
        
        # Сохраняем JSON
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка записи JSON: {e}")

def read_new_products():
    try:
        with open(new_products, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Ошибка в json: {e}")
        return {}

def get_category_emoji(categories):
    # Ищем подходящий смайлик для первой категории
    for category in categories:
        category_lower = category.lower()
        
        # Проверка для каждой категории с помощью регулярных выражений
        for key, pattern in CATEGORY_PATTERNS.items():
            if re.search(pattern, category_lower):  # Ищем по паттерну в категории
                return CATEGORY_EMOJIS[key]
    
    return "🍽️"  # По умолчанию смайлик для прочего

def create_dish_categories(filename):
    dish_categories = {}
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            # Убираем лишние пробелы и разделяем строку по ';'
            row = line.strip().split(';')
            if len(row) == 3:
                dish_name = row[0].strip()  # Название блюда
                categories = row[1].strip()  # Категории
                synonyms = row[2].strip()  # Синонимы
                # Объединяем название и синонимы в строку для поиска
                all_info = f"{dish_name}, {synonyms}"
                dish_categories[dish_name] = {"all_info": all_info, "categories": categories}
    return dish_categories

# Функция для поиска категорий с использованием fuzzywuzzy
from fuzzywuzzy import fuzz, process
from nltk.stem.snowball import RussianStemmer

def find_categories_fuzzy(dish_name, dish_categories, threshold=70, limit=5):
    # Пройдем по всем блюдам и используем fuzzywuzzy для поиска наиболее похожих
    stemmer = RussianStemmer()
    stemmed_dish_name = stemmer.stem(dish_name)
    matches = process.extract(
        stemmed_dish_name,
        [info["all_info"] for info in dish_categories.values()],
        scorer=fuzz.partial_ratio,
        limit=limit
    )

    # Учитываем длину строки
    def length_adjusted_score(match):
        match_text, score = match
        length_difference = abs(len(stemmed_dish_name) - len(match_text))
        # Уменьшаем оценку за большое расхождение в длине
        adjusted_score = score - length_difference
        return adjusted_score

    # Отсортируем по скорректированным оценкам
    matches = sorted(matches, key=length_adjusted_score, reverse=True)

    # Пройдем по всем результатам и фильтруем по порогу схожести
    for match in matches:
        best_match_info, score = match
        if score >= threshold:
            # Найдем ключ блюда, которое соответствует найденной строке
            best_match_dish = [dish for dish, info in dish_categories.items() if info["all_info"] == best_match_info][0]
            return dish_categories[best_match_dish]["categories"]

    return []

#database - json
file = 'fridge_data.json'
filename = 'dishes.txt'  # Путь к вашему файлу с данными
dish_categories = create_dish_categories(filename)

# Функции работы с данными
def read_json():
    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Преобразуем строки ISO обратно в объекты date
            for product in data:
                if product.get("manufacture_date"):
                    product["manufacture_date"] = datetime.date.fromisoformat(product["manufacture_date"])
                if product.get("expiry_date"):
                    product["expiry_date"] = datetime.date.fromisoformat(product["expiry_date"])
            return data
    except Exception as e:
        print(f"Ошибка чтения JSON: {e}")
        return []

def write_products(data):
    try:
        with open(new_products, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка записи продуктов: {e}")


# Добавление нового продукта
def start_adding_food(message):
    product_id = str(uuid.uuid4())  # Уникальный ID
    USER_STATE[message.chat.id] = {
        "state": "waiting_for_name",
        "product": {
            "id": product_id,
            "name": "",
            "categories" : [],
            "weight": 0,  # По умолчанию
            "tare_weight": 0,  # По умолчанию
            "source": "Магазин",  # По умолчанию
            "manufacture_date": datetime.date.today(),  # По умолчанию - сегодня
            "expiry_date": None,
        }
    }
    bot.send_message(message.chat.id, "Введите название продукта:", reply_markup=back_skip_markup)

def check_user_state(state=True):
    def decorator(func):
        def wrapper(message, *args, **kwargs):
            user_data = read_users()  # Читаем данные пользователей из файла
            user_id = str(message.from_user.id)  # Приводим идентификатор пользователя к строке
            if user_id in user_data:
                if user_data[user_id].get('enabled') == state:
                    return func(message, *args, **kwargs)  # Выполняем основную функцию
                else:
                    bot.send_message(message.chat.id, "Ваш аккаунт не активирован.")
            else:
                bot.send_message(message.chat.id, "Пока не нажмёте /start, работать не будет.")
        return wrapper
    return decorator


@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id, {}).get("state") == "waiting_for_name")
@check_user_state()
def get_food_name(message):
    if message.text == "Пропустить":
        bot.send_message(message.chat.id, "Название продукта нельзя пропустить. Пожалуйста, введите название.")
        return
    user_data = USER_STATE[message.chat.id]
    if message.text == "Назад":
        USER_STATE[message.chat.id]["state"] = "start"
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=start_markup)
        return 
    else:
        user_data["product"]["name"] = message.text
        user_data["state"] = "waiting_for_categories"
        cats = find_categories_fuzzy(message.text, dish_categories)
        user_data['product']['categories'] = cats
        bot.send_message(message.chat.id, f"Для продукта {message.text} автоматически определены следующие категории: {cats}. Их можно определить самому (напечатав через запятую и отправив), а можно оставить как есть (кнопка Пропустить)", reply_markup=back_skip_markup)

@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id, {}).get("state") == "waiting_for_categories")
@check_user_state()
def get_food_cats(message):
    if message.text == "Назад":
        go_back(message)
        return
    else:
        user_data = USER_STATE[message.chat.id]
        if message.text != "Пропустить":
            user_data["product"]["categories"] = message.text.split(",")
            bot.send_message(message.chat.id, "Категории обновлены.")
        user_data["state"] = "waiting_for_weight"
        bot.send_message(message.chat.id, "Введите вес продукта (граммы) или нажмите 'Пропустить':", reply_markup=back_skip_markup)

@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id, {}).get("state") == "waiting_for_weight")
@check_user_state()
def get_food_weight(message):
    if message.text == "Назад":
        go_back(message)
        return
    else:
        user_data = USER_STATE[message.chat.id]
        if message.text == "Пропустить":
            user_data["state"] = "waiting_for_tare_weight"
            bot.send_message(message.chat.id, "Введите вес тары (граммы) или нажмите 'Пропустить':", reply_markup=back_skip_markup)
            return

    try:
        weight = int(message.text)
        user_data["product"]["weight"] = weight
        user_data["state"] = "waiting_for_tare_weight"
        bot.send_message(message.chat.id, "Введите вес тары (граммы) или нажмите 'Пропустить':", reply_markup=back_skip_markup)
    except ValueError:
        bot.send_message(message.chat.id, "Введите корректный вес в граммах или нажмите 'Пропустить'.")

@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id, {}).get("state") == "waiting_for_tare_weight")
@check_user_state()
def get_food_tare_weight(message):
    if message.text == "Назад":
        go_back(message)
        return
    else:
        user_data = USER_STATE[message.chat.id]
        if message.text == "Пропустить":
            user_data["state"] = "waiting_for_source"
            bot.send_message(message.chat.id, "Кто приготовил продукт? (по умолчанию 'Магазин') или нажмите 'Пропустить':", reply_markup=back_skip_markup)
            return

    try:
        tare_weight = int(message.text)
        user_data["product"]["tare_weight"] = tare_weight
        user_data["state"] = "waiting_for_source"
        bot.send_message(message.chat.id, "Кто приготовил продукт? (по умолчанию 'Магазин') или нажмите 'Пропустить':", reply_markup=back_skip_markup)
    except ValueError:
        bot.send_message(message.chat.id, "Введите корректный вес тары в граммах или нажмите 'Пропустить'.")

@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id, {}).get("state") == "waiting_for_source")
@check_user_state()
def get_food_source(message):
    if message.text == "Назад":
        go_back(message)
        return
    else:
        user_data = USER_STATE[message.chat.id]
        if message.text == "Пропустить":
            user_data["state"] = "waiting_for_manufacture_date"
            bot.send_message(message.chat.id, "Выберите дату изготовления продукта на календаре или нажмите 'Пропустить':", reply_markup=calendar.create_calendar(calendar_1.prefix, datetime.datetime.now().year, datetime.datetime.now().month))
            return

    user_data["product"]["source"] = message.text if message.text else "Магазин"
    user_data["state"] = "waiting_for_manufacture_date"
    bot.send_message(message.chat.id, "Выберите дату изготовления продукта на календаре или нажмите 'Пропустить':", reply_markup=calendar.create_calendar(calendar_1.prefix, datetime.datetime.now().year, datetime.datetime.now().month))

@bot.callback_query_handler(func=lambda call: call.data.startswith(calendar_1.prefix))
@check_user_state()
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
        bot.send_message(call.message.chat.id, f"Выбрана дата: {chosen_date}. Укажите срок хранения (дни) или нажмите 'Пропустить':", reply_markup=back_skip_markup)

def get_summary(product, category_emoji, title):
    return (
        title,
        f"📌 **Название:** {product['name']}\n"
        f"{category_emoji} **Категория:** {product['categories']}\n"
        f"⚖️ **Вес:** {product['weight']} г\n"
        f"📦 **Вес тары:** {product['tare_weight']} г\n"
        f"🏷️ **Источник (кто приготовил):** {product['source']}\n"
        f"📅 **Дата изготовления:** {product['manufacture_date'].strftime('%d.%m.%Y')}\n"
        f"⏳ **Годен до:** {product['expiry_date'].strftime('%d.%m.%Y')}\n"
    )

def send_product_summary(chat_id, product):
    category_emoji = get_category_emoji(product["categories"])
    summary = get_summary(product,category_emoji, title="📝 **Проверьте данные продукта:**\n")
    bot.send_message(chat_id, summary, parse_mode="Markdown", reply_markup=check_markup)

@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id, {}).get("state") == "waiting_for_expiration_date")
@check_user_state()
def get_food_expiration_date(message):
    if message.text == "Назад":
        go_back(message)
        return
    else:
        user_data = USER_STATE[message.chat.id]
        if message.text == "Пропустить":
            product = user_data["product"]
            product["expiry_date"] = product["manufacture_date"] + datetime.timedelta(days=3)  # По умолчанию 3 дня
            user_data["state"] = "final_check"
            send_product_summary(message.chat.id, product)
            return

    try:
        days = int(message.text)
        product = user_data["product"]
        product["expiry_date"] = product["manufacture_date"] + datetime.timedelta(days=days)
        user_data["state"] = "final_check"
        send_product_summary(message.chat.id, product)
    except ValueError:
        bot.send_message(message.chat.id, "Введите срок хранения в днях или нажмите 'Пропустить'.")


@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id, {}).get("state") == "final_check")
@check_user_state()
def finalize_product(message):
    if message.text == "Сохранить":
        user_data = USER_STATE.pop(message.chat.id, None)
        if user_data:
            product = user_data["product"]
            data = read_json()
            data.append(product)
            write_json(fridge, data)
            bot.send_message(message.chat.id, "Продукт успешно сохранен!", reply_markup=start_markup)
            products_stream.on_next(USER_STATE[message.chat.id].get("product_id"), "registered")
    elif message.text == "Сброс":
        USER_STATE.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "Данные сброшены.", reply_markup=start_markup)

def notify_others_about_product(product_id, registering_user_id):
    product = read_new_products().get(product_id)
    if not product:
        return  # Продукт уже удален или не существует

    # Читаем список всех пользователей
    user_data = read_users()
    user_ids = [int(user_id) for user_id in user_data.keys()]

    # Исключаем регистрирующего пользователя
    user_ids = [user_id for user_id in user_ids if user_id != registering_user_id]
    # Текст сообщения
    product_info = get_summary(product,get_category_emoji(product["categories"]), title=f"✅ Новый продукт добавлен в базу!\n")

    # Отправляем сообщение всем остальным пользователям
    for user_id in user_ids:
        try:
            bot.send_message(user_id, product_info)
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id, {}).get("state") == "registering_product")
def finalize_registration(message):
    product_id = USER_STATE[message.chat.id].get("product_id")
    product = read_new_products().get(product_id)

    if product and product["user_id"] == message.from_user.id:
        # Завершаем регистрацию
        product["status"] = "registered"
        write_products(product["status"])
        products_stream.on_next((product_id, "registered"))

        # Отправляем пользователю сообщение о завершении
        bot.send_message(message.chat.id, "Продукт успешно зарегистрирован!")

        # Уведомляем всех остальных
        notify_others_about_product(product_id, message.from_user.id)
    else:
        bot.send_message(message.chat.id, "Ошибка регистрации. Попробуйте снова.")

@bot.message_handler(func=lambda message: message.text == "Новый продукт" or USER_STATE[message.chat.id]['state'] == 'adding_food')
@check_user_state()
def register_product(message):
    start_adding_food(message)

@bot.message_handler(func=lambda message: message.text == "Найди просрочку")
@check_user_state()
def check_expiration(message):
    bot.send_message(message.chat.id, "Эта функция пока не реализована. В будущем вы сможете увидеть продукты с истекающим сроком годности.")

@bot.message_handler(func=lambda message: message.text == "Удалить продукт")
@check_user_state()
def delete_product(message):
    bot.send_message(message.chat.id, "Функция удаления продукта находится в разработке.")

@bot.message_handler(func=lambda message: message.text == "Посоветуй вкусняшку")
@check_user_state()
def suggest_food(message):
    bot.send_message(message.chat.id, "Эта функция пока не реализована. В будущем вы сможете увидеть рекомендации, что приготовить.")

def read_users():
    try:
        with open(users, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def write_users(data):
    try:
        with open(users, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка записи пользователей: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username

    display_name = f"{first_name} {last_name}".strip() if last_name else first_name

    user_data = read_users()
    if user_id not in user_data:
        user_data[user_id] = {
            "enabled": True,
            "display_name": display_name,
            "username": username or "Без ника",
            "state" : ""
        }
        write_users(user_data)

    if int(user_id) == int(admin_id):
        bot.send_message(message.chat.id, "Режим админа включен", reply_markup=admin_markup)
    else:
        bot.send_message(
            message.chat.id, 
            "Добро пожаловать в Умный Холодильник Демо Версию!",
            reply_markup=start_markup
        )

@bot.message_handler(func=lambda message: message.text == "Сообщение от датчика веса")
@check_user_state()
def handle_weight_sensor(message):
    user_data = read_users()
    user_data[str(message.chat.id)]['state'] = 'dropping_food'
    write_users(user_data)
    bot.send_message(message.chat.id, "Сколько продуктов дропать?", reply_markup=drop_markup)


def add_new_weight_change(weight, chat_id):
    product_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now()
    products = read_new_products()
    if products is None:
        products = {}
    products[product_id] = {
        "weight": weight,
        "status": "waiting",  # waiting, in_progress, registered
        "user_id": None,
        "timestamp": timestamp,
        "message_id": None,  # ID сообщения для обновления
        "chat_id": chat_id
    }
    write_products(products)
    products_stream.on_next((product_id, "waiting"))

    return product_id

def edit_product_message(product_id, new_text):
    product = read_new_products().get(product_id)
    if product and product["message_id"]:
        bot.edit_message_text(
            chat_id=product["chat_id"],
            message_id=product["message_id"],
            text=new_text,
            reply_markup=create_product_markup(product_id)
        )

def create_product_markup(product_id):
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(
        text="Зарегистрировать продукт",
        callback_data=f"register:{product_id}"
    )
    markup.add(button)
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("register:"))
def register_product(call):
    try:
        product_id = call.data.split(":")[1]
        product = read_new_products().get(product_id)

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
        write_products(product)
        products_stream.on_next((product_id, "in_progress"))

        bot.answer_callback_query(call.id)
        USER_STATE[call.message.chat.id]['state'] = "adding_food"
        bot.send_message(call.message.chat.id, "Вы начали регистрацию продукта. Сначала надо ввести имя продукта, который хотите зарегистрировать")
    except Exception as e:
        print(e)
        bot.send_message(call.message.chat.id, "Бот не знает, что делать(((")

@bot.message_handler(func=lambda message: read_users()[str(message.chat.id)]['state'] == "dropping_food")
@check_user_state()
def drop_food(message):
    num = int(message.text)
    products = read_new_products()
    for _ in range(num):
        random_weight = random.randint(100, 1100)
        product_id = add_new_weight_change(random_weight, message.chat.id)
        msg = (
        "📦 ***Обнаружен новый продукт!***\n\n"
        f"📊 **Вес продукта:** {random_weight} г\n"
        "❓ Кто-то положил это в холодильник, но мы пока не знаем, что это.\n\n"
        "👇 Нажмите кнопку ниже, чтобы зарегистрировать этот продукт."
    )
        markup = create_product_markup(product_id)
        bot.send_message(
            message.chat.id,
            msg,
            reply_markup=markup,
            parse_mode="Markdown"
        )

        # Убедимся, что продукт существует в списке
        if product_id not in products:
            products[product_id] = {
                "weight": 0,  # Или другое значение по умолчанию
                "status": "waiting",
                "user_id": None,
                "timestamp": datetime.datetime.now().isoformat(),
                "message_id": None,
                "chat_id": None
            }

        # Обновляем данные продукта
        products[product_id]["message_id"] = message.chat.id

        # Сохраняем изменения
        write_products(products)




@bot.message_handler(func=lambda message: message.text == "Рандомный продукт")
@check_user_state()
def handle_random_product(message):
    bot.send_message(message.chat.id, "Вот случайный продукт из вашего холодильника!")

#кнопка НАЗАД
@bot.message_handler(func=lambda message: message.text == "Назад")
@check_user_state()
def go_back(message):
    try:
        previous_state = USER_STATE.get(message.chat.id, {}).get("state")

        # Обновляем состояние в USER_STATE в зависимости от предыдущего шага
        if previous_state == "waiting_for_name":
            # Возвращаем к шагу выбора названия продукта
            USER_STATE[message.chat.id]["state"] = "start"
            bot.send_message(message.chat.id, "Выберите действие:", reply_markup=start_markup)
        elif previous_state == "waiting_for_weight":
            # Возвращаем к шагу ввода веса
            USER_STATE[message.chat.id]["state"] = "waiting_for_name"
            bot.send_message(message.chat.id, "Введите название продукта:", reply_markup=back_skip_markup)
        elif previous_state == "waiting_for_tare_weight":
            # Возвращаем к шагу ввода веса тары
            USER_STATE[message.chat.id]["state"] = "waiting_for_weight"
            bot.send_message(message.chat.id, "Введите вес продукта (граммы):", reply_markup=back_skip_markup)
        elif previous_state == "waiting_for_source":
            # Возвращаем к шагу ввода источника
            USER_STATE[message.chat.id]["state"] = "waiting_for_tare_weight"
            bot.send_message(message.chat.id, "Введите вес тары (граммы):", reply_markup=back_skip_markup)
        elif previous_state == "waiting_for_manufacture_date":
            # Возвращаем к шагу ввода даты изготовления
            USER_STATE[message.chat.id]["state"] = "waiting_for_source"
            bot.send_message(message.chat.id, "Кто приготовил продукт? (по умолчанию 'Магазин'):", reply_markup=back_skip_markup)
        elif previous_state == "waiting_for_expiration_date":
            # Возвращаем к шагу ввода срока годности
            USER_STATE[message.chat.id]["state"] = "waiting_for_manufacture_date"
            bot.send_message(message.chat.id, "Выберите дату изготовления продукта на календаре:", reply_markup=calendar.create_calendar(calendar_1.prefix, datetime.now.year, datetime.now.month))
        else:
            # Если шаг не определен, возвращаем на стартовое меню
            USER_STATE[message.chat.id]["state"] = "start"
            bot.send_message(message.chat.id, "Выберите действие:", reply_markup=start_markup)

    except:
        # Если в стеке нет состояния, возвращаем на стартовое меню
        USER_STATE[message.chat.id]["state"] = "start"
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=start_markup)
        
products_stream.pipe(
    # Фильтруем продукты, которые устарели (старше 1 дня)
    ops.map(lambda event: (event[0], read_new_products().get(event[0]))),  # Извлекаем данные продукта
    ops.filter(lambda event: event[1] is not None),  # Убираем случаи, когда продукт отсутствует
    ops.filter(lambda event: (datetime.datetime.now() - datetime.datetime.fromisoformat(event[1]["timestamp"])).total_seconds() > 86400),
).subscribe(
    lambda event: notify_and_delete_expired_product(event[0], event[1])
)


def notify_and_delete_expired_product(product_id, product):
    if product:
        # Удаляем продукт из хранилища
        
        product.remove(product["product_id"])
        write_products(product)

        # Редактируем сообщение об этом продукте
        edit_product_message(product_id, "💤 Уже неактуально - прошло слишком много времени")

products_stream.pipe(
    # Фильтрация событий для редактирования сообщений
    ops.filter(lambda event: event[1] == "in_progress"),
    ops.filter(lambda event: event[0] is not None),
).subscribe(lambda event: edit_product_message(event[0], "UPD: Продукт уже регистрируют."))

products_stream.pipe(
    # Фильтрация событий для регистрации
    ops.filter(lambda event: event[1] == "registered"),
    ops.filter(lambda event: event[0] is not None),
).subscribe(lambda event: edit_product_message(event[0], "✅ Продукт успешно зарегистрирован!"))

bot.polling()
