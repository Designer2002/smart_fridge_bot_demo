from config import *
from utils import find_categories_fuzzy, find_emoji_fuzzy, get_random_weight
from rx import operators as ops
import uuid
from telebot import TeleBot, types
import datetime

from telebot import TeleBot


bot = TeleBot(bot_token)







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
    category_emoji = find_emoji_fuzzy(product["categories"])
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
    product_info = get_summary(product,find_emoji_fuzzy(product["categories"]), title=f"✅ Новый продукт добавлен в базу!\n")

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
        random_weight = get_random_weight(100,1100)
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

if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling()
