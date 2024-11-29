import configparser
import datetime
from functools import lru_cache
from random import randint
import uuid
from fuzzywuzzy import fuzz, process
from nltk.stem.snowball import RussianStemmer
from bot.editors import edit_product_message
from bot.emoji import CATEGORY_NAMES, CATEGORY_EMOJIS
from bot.markups import back_skip_markup, check_markup

def find_emoji_fuzzy(dish_name, threshold=70):
    flat_category_names = []
    category_map = {}

    for category, names in CATEGORY_NAMES.items():
        for name in names:
            flat_category_names.append(name)
            category_map[name] = category

    match = process.extractOne(dish_name, flat_category_names, scorer=fuzz.partial_ratio)
    if match and match[1] >= threshold:
        matched_category = category_map[match[0]]
        return CATEGORY_EMOJIS.get(matched_category, CATEGORY_EMOJIS["прочее"])

    return CATEGORY_EMOJIS["прочее"]

@lru_cache(maxsize=1000)
def stem_text(text):
    stemmer = RussianStemmer()
    return stemmer.stem(text)

def find_categories_fuzzy(dish_name, dish_categories, threshold=70, limit=5):
    # Пройдем по всем блюдам и используем fuzzywuzzy для поиска наиболее похожих
    stemmer = RussianStemmer()
    stemmed_dish_name = stem_text(dish_name)
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

def check_user_state(state=True):
    def decorator(bot, func):
        async def wrapper(message, *args, **kwargs):
            from utils.database import read_json
            user_data = read_json()  # Читаем данные пользователей из файла
            user_id = str(message.from_user.id)  # Приводим идентификатор пользователя к строке
            if user_id in user_data:
                if user_data[user_id].get('enabled') == state:
                    return func(message, *args, **kwargs)  # Выполняем основную функцию
                else:
                    await bot.send_message(message.chat.id, "Ваш аккаунт не активирован.")
            else:
                await bot.send_message(message.chat.id, "Пока не нажмёте /start, работать не будет.")
        return wrapper
    return decorator

def check_if_correct_data(data):
    for product in data:
        if isinstance(product.get("manufacture_date"), datetime.date):
            product["manufacture_date"] = product["manufacture_date"].isoformat()
        if isinstance(product.get("expiry_date"), datetime.date):
            product["expiry_date"] = product["expiry_date"].isoformat()
    return data

def notify_and_delete_expired_product(product_id, product):
    from utils.database import write_json
    if product:
        # Удаляем продукт из хранилища
        
        product.remove(product["product_id"])
        write_json(product)

        # Редактируем сообщение об этом продукте
        edit_product_message(product_id, "💤 Уже неактуально - прошло слишком много времени")

def add_new_weight_change(weight, chat_id):
    from config import new_products
    from event_handlers import products_stream
    from utils.database import read_json, write_json
    product_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now()
    products = read_json(new_products)
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
    write_json(new_products, products)
    products_stream.on_next((product_id, "waiting"))

    return product_id

# Добавление нового продукта
async def start_adding_food(bot, message):
    from message_handler import registration_sessions
    product_id = str(uuid.uuid4())  # Уникальный ID
    registration_sessions[message.chat.id] = {
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
    await bot.send_message(message.chat.id, "Введите название продукта:", reply_markup=back_skip_markup)

async def notify_others_about_product(bot, product_id, registering_user_id):
        from config import new_products, users
        from utils.database import read_json
        product = read_json(new_products).get(product_id)
        if not product:
            return  # Продукт уже удален или не существует

        # Читаем список всех пользователей
        user_data = read_json(users)
        user_ids = [int(user_id) for user_id in user_data.keys()]

        # Исключаем регистрирующего пользователя
        user_ids = [user_id for user_id in user_ids if user_id != registering_user_id]
        # Текст сообщения
        product_info = get_summary(product,find_emoji_fuzzy(product["categories"]), title=f"✅ Новый продукт добавлен в базу!\n")

        # Отправляем сообщение всем остальным пользователям
        for user_id in user_ids:
            try:
                await bot.send_message(user_id, product_info)
            except Exception as e:
                print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
                
def get_random_weight(a,b):
    return randint(a, b)

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

async def send_product_summary(bot, chat_id, product):
    category_emoji = find_emoji_fuzzy(product["categories"])
    summary = get_summary(product,category_emoji, title="📝 **Проверьте данные продукта:**\n")
    await bot.send_message(chat_id, summary, parse_mode="Markdown", reply_markup=check_markup)

def create_config():
    # Создаем объект ConfigParser
    config = configparser.ConfigParser()
    
    # Добавляем данные без секций
    config['DEFAULT'] = {
        'admin_id': '699861867',
        'bot_token': "7223871421:AAG2IKwKcGALr5UUYbs15LI9ndd8xpS1FpQ",
        'sessions_file': 'data/registration_sessions.json',
        'fridge': 'data/fridge_data.json',
        'users': 'data/users.json',
        'new_products': 'data/new_products.json',
        'interactive': 'data/state.json',
        'dishes': 'data/dishes.txt'
    }
    
    # Записываем конфигурацию в файл
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def read_config():
    # Создаем объект ConfigParser
    config = configparser.ConfigParser()

    # Читаем конфигурацию из файла
    config.read('config.ini')

    # Преобразуем данные в словарь
    config_data = dict(config['DEFAULT'])

    return config_data