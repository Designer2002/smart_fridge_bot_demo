from telebot import TeleBot, types
import json
#from nltk.stem.snowball import RussianStemmer
import datetime
#from fuzzywuzzy import fuzz
#from fuzzywuzzy import process
import telebot_calendar
from telebot_calendar import Calendar, CallbackData, RUSSIAN_LANGUAGE
bot = TeleBot("7223871421:AAG2IKwKcGALr5UUYbs15LI9ndd8xpS1FpQ")
SUGGEST_FOOD = 'Что покушать можно?'
CHECK_EXPIRATION = 'Проверить сроки годности'
ADD_FOOD='Зарегистировать продукт'
DELETE_FOOD="Удалить продукт"
BACK = 'Назад'
ERROR = 'Бот потерялся и запутался :(\nПопробуйте еще раз'
FOOD_NAME = 'Название'
FOOD_WEIGHT = 'Масса еды (вместе с контейнером, если он есть)'
FOOD_TARE_WEIGHT = 'Масса контейнера, где лежит еда (можно пропустить при отсутствии)'
FOOD_SOURCE = 'Откуда еда (имя того, кто готовил, либо пропустите это поле - по умолчанию будет выбран "Магазин")'
RESET = 'Сброс'
EDIT_CAT = 'Записать категории вручную'
EDIT_MAN = 'Установить свою дату(через календарь)'
CONTINUE = 'Продолжить'
SKIP = 'Пропустить этот пункт'
APPLY = 'Сохранить'



# Состояние пользователя
USER_STATE = {}
USER_STACK = []

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
def find_categories_fuzzy(dish_name, dish_categories, threshold=50, limit=5):
    # Пройдем по всем блюдам и используем fuzzywuzzy для поиска наиболее похожих
    stemmer = RussianStemmer()
    matches = process.extract(stemmer.stem(dish_name), [info["all_info"] for info in dish_categories.values()], scorer=fuzz.partial_ratio, limit=limit)

    # Пройдем по всем результатам и фильтруем по порогу схожести
    best_match = None
    for match in matches:
        if match[1] >= threshold:
            best_match_info = match[0]
            # Найдем ключ блюда, которое соответствует найденной строке
            best_match_dish = [dish for dish, info in dish_categories.items() if info["all_info"] == best_match_info][0]
            best_match = dish_categories[best_match_dish]
            break
    if best_match:
        return best_match["categories"]
    else:
        return []

#database - json
file = 'fridge_data.json'
filename = 'dishes.txt'  # Путь к вашему файлу с данными
#dish_categories = create_dish_categories(filename)


calendar = Calendar(language=RUSSIAN_LANGUAGE)
calendar_1 = CallbackData('calendar_1', 'action', 'year', 'month', 'day')
now = datetime.datetime.now()

back_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
back_markup.add(types.KeyboardButton(BACK))

start_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
c1 = types.KeyboardButton(SUGGEST_FOOD)
c2 = types.KeyboardButton(CHECK_EXPIRATION)
c3 = types.KeyboardButton(ADD_FOOD)
c4 = types.KeyboardButton(DELETE_FOOD)
start_markup.add(c1, c2, c4, c3)

add_cat_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
c1 = types.KeyboardButton(EDIT_CAT)
c2= types.KeyboardButton(CONTINUE)#--> weight
reset = types.KeyboardButton(RESET)
add_cat_markup.add(c1,c2,reset)

add_weight_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
c2= types.KeyboardButton(SKIP) #to source
reset = types.KeyboardButton(RESET)
add_weight_markup.add(c2,reset)

add_tare_weight_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
c2= types.KeyboardButton(SKIP)#to source
reset = types.KeyboardButton(RESET)
add_tare_weight_markup.add(c2,reset)

add_source_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
c2= types.KeyboardButton(CONTINUE)#to man date
reset = types.KeyboardButton(RESET)
add_source_markup.add(c2, reset)

add_date_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
c2= types.KeyboardButton(CONTINUE) #to exp date
reset = types.KeyboardButton(RESET)
add_date_markup.add(c2,reset)

add_exp_date_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
c2= types.KeyboardButton(SKIP)
reset = types.KeyboardButton(RESET)
add_exp_date_markup.add(c2,reset)

check_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
c2= types.KeyboardButton(APPLY)
reset = types.KeyboardButton(RESET)
check_markup.add(c2,reset)

empty_json_data = []  
with open(file, "w", encoding="utf-8") as f:
    json.dump(empty_json_data, f, indent=4)



product_name = ""
categories = []
source = "Магазин"
m_date = datetime.date.today()
e_date = datetime.date.today()
weight = 0
t_weight = 0

#TRY PARSE 
def ignore_exception(IgnoreException=Exception,DefaultVal=None):
    """ Decorator for ignoring exception from a function
    e.g.   @ignore_exception(DivideByZero)
    e.g.2. ignore_exception(DivideByZero)(Divide)(2/0)
    """
    def dec(function):
        def _dec(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except IgnoreException:
                return DefaultVal
        return _dec
    return dec

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Добро пожаловать в Умный Холодильник Демо Версию! Как говорится, без еды, как без воды - ни туды и ни сюды, так что дожидаемся начала интерактива и заполним же наш холодильник! ", reply_markup=start_markup)


@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id) == "categories_entered")
def weight_asker(message):
    USER_STATE[message.chat.id] = 'waiting_for_weight'
    USER_STACK.append(message)
    bot.send_message(message.chat.id, f"Введите вес продукта (просто целое число в граммах)", reply_markup=add_weight_markup)


def edit_cat(message):
    USER_STATE[message.chat.id] = "editing_category"  # Переходим к следующему состоянию
    bot.send_message(message.chat.id, "Введите категории самостоятельно через запятую", reply_markup=back_markup)

@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id) == "editing_category")
def after_editing_cats(message):
    try:
        if message.text == BACK:
            USER_STATE[message.chat.id] = "adding_categories"
            get_food_name(USER_STACK.pop())
        else:
            cats = message.text.split(",")
            USER_STATE[message.chat.id] = "categories_entered"
            bot.send_message(message.chat.id,f"Присвоены следующие категории:\n{cats}", reply_markup=add_cat_markup)
    except Exception as e:
        print (e)
        bot.send_message(message.chat.id,ERROR, reply_markup=back_markup)

        

@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id) == "waiting_for_weight")
def get_food_weight(message):
    try:
        if message.text == RESET:
            start_adding_food(message)
        elif message.text == BACK:
            weight_asker(USER_STACK.pop())
        else:
            sint = ignore_exception(ValueError)(int)
            global weight
            weight = sint(message.text.split(" ")[0])  # Получаем вес
            if weight and weight != 0:
                USER_STATE[message.chat.id] = "waiting_for_tare_weight"  # Переходим к следующему состоянию
                bot.send_message(message.chat.id, f"Вес продукта: {weight} г. Теперь укажите вес тары (это необязательно):", reply_markup=add_tare_weight_markup)
            else:
                USER_STATE[message.chat.id] = "waiting_for_source"  # Переходим к следующему состоянию
                bot.send_message(message.chat.id, f'Вес продукта не указан. Переход к следующему шагу. Кто готовил еду? (по умолчанию это магазин)', reply_markup=add_source_markup)
    except Exception as e:
        print (e)
        bot.send_message(message.chat.id, ERROR, reply_markup=back_markup)


@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id) == "waiting_for_tare_weight")
def get_food_tare_weight(message):
    try:
        if message.text == RESET:
            start_adding_food(message)
        else:
            sint = ignore_exception(ValueError)(int)
            tare_weight = sint(message.text.split(" ")[0])  # Получаем вес тары
            calced_weight = 0
            if tare_weight:
                global t_weight
                t_weight = tare_weight
                calced_weight = tare_weight
            USER_STATE[message.chat.id] = "waiting_for_source"  # Переходим к следующему состоянию
            bot.send_message(message.chat.id, f"Вес тары: {calced_weight} г. Теперь укажите того, кто готовил (по умолчанию установлено, что еда магазинная):", reply_markup=add_source_markup)
    except Exception as e:
        print (e)
        bot.send_message(message.chat.id, ERROR, reply_markup=back_markup)

@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id) == "waiting_for_source")
def get_food_source(message):
    global source
    if message.text == RESET:
        start_adding_food(message)
    else:
        source = message.text if message.text != CONTINUE else "Магазин"  # Используем "Магазин", если поле пустое
        USER_STATE[message.chat.id] = "waiting_for_manufacture_date"  # Переходим к следующему состоянию
        USER_STACK.append(message)
        bot.send_message(message.chat.id, f"Источник: {source}. Теперь укажите дату изготовления (на календаре):", reply_markup=calendar.create_calendar(
            name=calendar_1.prefix,
            year=now.year,
            month=now.month)
            )

@bot.callback_query_handler(func=lambda call: call.data.startswith(calendar_1.prefix))
def get_food_manufacture_date(call):
    try:
        name, action, year, month, day = call.data.split(calendar_1.sep)
        # Processing the calendar. Get either the date or None if the buttons are of a different type
        chosen_date = datetime.date(year, month, day)
        # There are additional steps. Let's say if the date DAY is selected, you can execute your code. I sent a message.
        if action == "DAY":
            manufacture_date = datetime.strptime(call.message.text, "%d.%m.%Y") if call.message != SKIP else now # Преобразуем строку в дату
            global m_date
            m_date = chosen_date
            USER_STATE[call.message.chat.id] = "waiting_for_expiration_date"  # Переходим к следующему состоянию
            bot.send_message(call.message.chat.id, f"Дата изготовления: {chosen_date.strftime('%d.%m.%Y')}. Сколько хранится продукт? (по умолчанию 3 дня):")
        elif action == "CANCEL":
            get_food_source(USER_STACK.pop())
    except Exception as e:
        print (e)
        bot.send_message(call.message.chat.id, ERROR, reply_markup=back_markup)

@bot.callback_query_handler(func=lambda call: call.data == 'waiting_for_expiration_date')
def get_food_exp_date(message):
    try:
        sint = ignore_exception(ValueError)(int)
        global e_date
        e_date = sint(message.text.split(" ")[0])  # Получаем вес
        
        USER_STATE[message.chat.id] = "waiting_for_check"  # Переходим к следующему состоянию
        global product_name,categories,source,m_date,weight,t_weight
        bot.send_message(message.chat.id, f'Подводим итоги: \n------------------\n{product_name}\nКатегории: {categories}\nОткуда продукт (кто готовил): {source}, Масса нетто(без тары): {weight-t_weight}\n Дата изготовления: {m_date}\n Срок годности: {e_date}\n', reply_markup=check_markup)
    except Exception as e:
        print (e)
        bot.send_message(message.chat.id, ERROR, reply_markup=back_markup)


def start_adding_food(message):
    try:
        USER_STATE[message.chat.id] = "waiting_for_name"  # Сохраняем состояние
        bot.send_message(message.chat.id, "Отлично! Начнём с названия блюда - его надо ввести в чат. Будет несколько полей, но не все обязательные.", reply_markup=back_markup)
    except Exception as e:
        print(e)

@bot.message_handler(func=lambda message: USER_STATE.get(message.chat.id) == "waiting_for_name")
def get_food_name(message):
    try:
        reserved = [ADD_FOOD, SUGGEST_FOOD, CHECK_EXPIRATION, DELETE_FOOD]
        global product_name
        product_name = message.text 
        if message.text == BACK:
            handle_message(message)
            return
        elif message.text not in reserved:
            #cats = find_categories_fuzzy(message.text, dish_categories)
            cats = ['Соевое мясо', 'Пластилиновый маргарин']
            msg = ""
            if len(cats) > 0:
                msg = f"Для продукта {message.text} автоматически определены категории:\n{cats}\nКатегории можно переписать вручную (формат ввода - через запятую)\n"
            else:
                msg = f"Не удалось определить категории для продукта {message.text}. Укажите их вручную, если хотите (формат ввода - через запятую)"
            global categories
            categories = cats  # Используем найденные категории
            USER_STATE[message.chat.id] = "categories_entered"
            USER_STACK.append(message)
            bot.send_message(message.chat.id, msg, reply_markup=add_cat_markup)
        else:
            handle_message(message)
            return
        
    except Exception as e:
        print (e)
        bot.send_message(message.chat.id,ERROR, reply_markup=back_markup)


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        if message.text == SUGGEST_FOOD:
            bot.send_message(message.chat.id, make_food_suggestions(), reply_markup = back_markup)
        elif message.text == CHECK_EXPIRATION:
            bot.send_message(message.chat.id, check_expire(),reply_markup = back_markup)
        elif message.text == BACK:
            bot.send_message(message.chat.id, "Выберите опцию:", reply_markup=start_markup)
        elif message.text == ADD_FOOD or message.text == RESET:
            start_adding_food(message)
        elif message.text == EDIT_CAT:
            edit_cat(message)
        else: "Я так не умею :("
    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, ERROR,reply_markup = back_markup)

def write_json(data):
    try:
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка записи JSON: {e}")

def make_food_suggestions():
    try:
        data = read_json()
        if not data:
            return "А кушать нечего :("
        result = "Можно съесть следующие продукты:\n"
        for item in data:
            result += f"{item['name']}\nИнформация:\nКто приготовил(откуда продукт): {item['source']}\nМасса продукта без упаковки: {item['net_weight']}\nДата изготовления: {item['manufacture_date']}\nГоден до: {item['expiry_date']}\n--------------\nДополнительная информация:\nКатегория: {', '.join(item['categories'])}\n\n"
        return result
    except Exception as e:
        print(f"Ошибка в make_food_suggestions: {e}")
        return ERROR
    
    
def check_expire():
    try:
        return "Портиться нечему :("
    except:
        return ERROR
    
def read_json():
     with open(file, "r", encoding="utf-8") as f:
        fridge_data = json.load(f)
        return fridge_data
        #for item in fridge_data:
            #print(f"Название продукта: {item['name']}, Срок годности: {item['expiry_date']}")

def insert_data(name, weight, tare_weight=0, source='Магазин', categories=[], man_date=datetime.date.today(), exp_date=3):
    try:
        data = read_json()
        new_item = {
            "name": name,
            "source": source,
            "weight": weight,
            "tare_weight": tare_weight,
            "net_weight": weight - tare_weight,
            "categories": categories,
            "manufacture_date": man_date.isoformat(),
            "expiry_date": (man_date + datetime.timedelta(days=exp_date)).isoformat()
            #"ingredients": ingredients
        }
        data.append(new_item)
        write_json(data)
    except Exception as e:
        print(f"Ошибка в insert_data: {e}")


# Запуск бота
bot.polling()
