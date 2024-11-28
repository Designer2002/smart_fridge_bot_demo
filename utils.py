import datetime
from random import randint
import uuid
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from nltk.stem.snowball import RussianStemmer
from config import USER_STATE
from json_database import write_json, read_json
from handlers.editors import edit_product_message
from markups import back_skip_markup

CATEGORY_EMOJIS = {
    "овощ": "🥦",    # Овощи
    "молоч": "🥛",   # Молочные продукты
    "мясо": "🍖",    # Мясо
    "рыба": "🐟",    # Рыба
    "фрукт": "🍎",   # Фрукты
    "выпечка": "🥐", # Выпечка
    "хлеб": "🍞",    # Хлеб
    "прочее": "🍽️"  # Прочее
}

CATEGORY_NAMES = {
    "овощ": ["овощ", "овощной", "овощная", "овощи", "овощное", "овощные"],
    "молоко": ["молочный", "молочное", "молочные"],
    "мясо": ["мясо", "мясной", "мясные", "мясное"],
    "рыба": ["рыба", "рыбный", "рыбные", "рыбное"],
    "фрукт": ["фрукт", "фрукты", "фруктовый"],
    "выпечка": ["выпечка", "выпеченные", "печёное"],
    "хлеб": ["хлеб", "хлебный", "хлебная", "хлебное"],
}

def get_random_weight(a,b):
    return randint(a, b)

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


def find_emoji_fuzzy(dish_name, threshold=70):
    # Создаём список для поиска
    flat_category_names = []
    category_map = {}

    for category, names in CATEGORY_NAMES.items():
        for name in names:
            flat_category_names.append(name)
            category_map[name] = category

    # Ищем наиболее подходящую категорию
    match = process.extractOne(dish_name, flat_category_names, scorer=fuzz.partial_ratio)
    if match and match[1] >= threshold:  # Проверяем порог схожести
        matched_category = category_map[match[0]]
        return CATEGORY_EMOJIS.get(matched_category, CATEGORY_EMOJIS["прочее"])

    return CATEGORY_EMOJIS["прочее"]

def check_if_correct_data(data):
    for product in data:
        if isinstance(product.get("manufacture_date"), datetime.date):
            product["manufacture_date"] = product["manufacture_date"].isoformat()
        if isinstance(product.get("expiry_date"), datetime.date):
            product["expiry_date"] = product["expiry_date"].isoformat()
    return data

def notify_and_delete_expired_product(product_id, product):
    if product:
        # Удаляем продукт из хранилища
        
        product.remove(product["product_id"])
        write_json(product)

        # Редактируем сообщение об этом продукте
        edit_product_message(product_id, "💤 Уже неактуально - прошло слишком много времени")

# Добавление нового продукта
def start_adding_food(bot, message):
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
    def decorator(bot, func):
        def wrapper(message, *args, **kwargs):
            user_data = read_json()  # Читаем данные пользователей из файла
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