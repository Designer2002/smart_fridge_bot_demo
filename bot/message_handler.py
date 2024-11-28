import datetime
from telebot.async_telebot import AsyncTeleBot
from utils.helpers import add_new_weight_change, find_categories_fuzzy, get_random_weight, notify_others_about_product, send_product_summary, start_adding_food
from bot.markups import back_skip_markup, create_product_markup, start_markup, drop_markup, admin_markup
from utils.helpers import check_user_state
from config import interactive_state, new_products, users, fridge, products_stream, dishes, calendar, calendar_1, registration_sessions
from utils.database import read_json, write_json

async def handle_messages(bot: AsyncTeleBot):
    @bot.message_handler(func=lambda message: message.text == "Назад")
    @check_user_state()
    async def go_back(message):
        try:
            user_data = registration_sessions.setdefault(message.chat.id, {})
            previous_state = user_data.get("state", "start")

            if previous_state == "waiting_for_name":
                user_data["state"] = "start"
                await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=start_markup)
            elif previous_state == "waiting_for_weight":
                user_data["state"] = "waiting_for_name"
                await bot.send_message(message.chat.id, "Введите название продукта:", reply_markup=back_skip_markup)
            elif previous_state == "waiting_for_tare_weight":
                user_data["state"] = "waiting_for_weight"
                await bot.send_message(message.chat.id, "Введите вес продукта (граммы):", reply_markup=back_skip_markup)
            elif previous_state == "waiting_for_source":
                user_data["state"] = "waiting_for_tare_weight"
                await bot.send_message(message.chat.id, "Введите вес тары (граммы):", reply_markup=back_skip_markup)
            elif previous_state == "waiting_for_manufacture_date":
                user_data["state"] = "waiting_for_source"
                await bot.send_message(message.chat.id, "Кто приготовил продукт? (по умолчанию 'Магазин'):", reply_markup=back_skip_markup)
            elif previous_state == "waiting_for_expiration_date":
                user_data["state"] = "waiting_for_manufacture_date"
                await bot.send_message(
                    message.chat.id, 
                    "Выберите дату изготовления продукта на календаре:", 
                    reply_markup=calendar.create_calendar(calendar_1.prefix, datetime.datetime.now().year, datetime.datetime.now().month)
                )
            else:
                user_data["state"] = "start"
                await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=start_markup)

        except Exception:
            registration_sessions[message.chat.id] = {"state": "start"}
            await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=start_markup)


    @bot.message_handler(func=lambda message: registration_sessions.get[str(message.chat.id)]['state'] == "dropping_food")
    @check_user_state()
    def drop_food(message):
        num = int(message.text)
        products = read_json(products)
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
            write_json(new_products, products)

    @bot.message_handler(func=lambda message: message.text == "Рандомный продукт")
    @check_user_state()
    async def handle_random_product(message):
        await bot.send_message(message.chat.id, "Вот случайный продукт из вашего холодильника!")

    @bot.message_handler(func=lambda message: message.text == "Сообщение от датчика веса")
    @check_user_state()
    async def handle_weight_sensor(message):
        registration_sessions[str(message.chat.id)]['state'] = 'dropping_food'
        await bot.send_message(message.chat.id, "Сколько продуктов дропать?", reply_markup=drop_markup)
    
    @bot.message_handler(func=lambda message: message.text == "Начать интерактив")
    @check_user_state()
    async def start_interactive(message):
        interactive_state.on_next(True)  # Обновляем состояние потока
        await bot.send_message(message.chat.id, "Интерактив начался! Все пользователи могут пользоваться ботом.", reply_markup=admin_markup)

    @bot.message_handler(func=lambda message: message.text == "Новый продукт" or registration_sessions[message.chat.id]['state'] == 'adding_food')
    @check_user_state()
    async def register_product(message):
        await start_adding_food(message)

    @bot.message_handler(func=lambda message: message.text == "Найди просрочку")
    @check_user_state()
    async def check_expiration(message):
        await bot.send_message(message.chat.id, "Эта функция пока не реализована. В будущем вы сможете увидеть продукты с истекающим сроком годности.")

    @bot.message_handler(func=lambda message: message.text == "Удалить продукт")
    @check_user_state()
    async def delete_product(message):
        await bot.send_message(message.chat.id, "Функция удаления продукта находится в разработке.")

    @bot.message_handler(func=lambda message: message.text == "Посоветуй вкусняшку")
    @check_user_state()
    async def suggest_food(message):
        await bot.send_message(message.chat.id, "Эта функция пока не реализована. В будущем вы сможете увидеть рекомендации, что приготовить.")

    @bot.message_handler(func=lambda message: registration_sessions(users).get(message.chat.id, {}).get("state") == "waiting_for_expiration_date")
    @check_user_state()
    async def get_food_expiration_date(message):
        if message.text == "Назад":
            go_back(message)
            return
        else:
            if message.text == "Пропустить":
                product = registration_sessions["product"]
                registration_sessions["expiry_date"] = product["manufacture_date"] + datetime.timedelta(days=3)  # По умолчанию 3 дня
                registration_sessions["state"] = "final_check"
                await send_product_summary(message.chat.id, product)
                return

        try:
            days = int(message.text)
            product = registration_sessions["product"]
            registration_sessions["expiry_date"] = product["manufacture_date"] + datetime.timedelta(days=days)
            registration_sessions["state"] = "final_check"
            await send_product_summary(message.chat.id, product)
        except ValueError:
            await bot.send_message(message.chat.id, "Введите срок хранения в днях или нажмите 'Пропустить'.")


    @bot.message_handler(func=lambda message: registration_sessions.get(message.chat.id, {}).get("state") == "final_check")
    @check_user_state()
    async def finalize_product(message):
        if message.text == "Сохранить":
            user_data = registration_sessions.pop(message.chat.id, None)
            if user_data:
                product = user_data["product"]
                data = read_json()
                data.append(product)
                write_json(fridge, data, True)
                await bot.send_message(message.chat.id, "Продукт успешно сохранен!", reply_markup=start_markup)
                products_stream.on_next(read_json(users)[message.chat.id].get("product_id"), "registered")
        elif message.text == "Сброс":
            await bot.send_message(message.chat.id, "Данные сброшены.", reply_markup=start_markup)


    @bot.message_handler(func=lambda message: registration_sessions.get(message.chat.id, {}).get("state") == "registering_product")
    async def finalize_registration(message):
        product_id = registration_sessions[message.chat.id].get("product_id")
        product = registration_sessions

        if product and product["user_id"] == message.from_user.id:
            # Завершаем регистрацию
            product["status"] = "registered"
            write_json(new_products, product["status"])
            products_stream.on_next((product_id, "registered"))

            # Отправляем пользователю сообщение о завершении
            await bot.send_message(message.chat.id, "Продукт успешно зарегистрирован!")

            # Уведомляем всех остальных
            await notify_others_about_product(product_id, message.from_user.id)
        else:
            await bot.send_message(message.chat.id, "Ошибка регистрации. Попробуйте снова.")

    @bot.message_handler(func=lambda message: registration_sessions.get(message.chat.id, {}).get("state") == "waiting_for_name")
    @check_user_state()
    async def get_food_name(message):
        if message.text == "Пропустить":
            bot.send_message(message.chat.id, "Название продукта нельзя пропустить. Пожалуйста, введите название.")
            return
        if message.text == "Назад":
            registration_sessions[message.chat.id]['state'] = "start"
            await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=start_markup)
            return 
        else:
            registration_sessions["product"]["name"] = message.text
            registration_sessions["state"] = "waiting_for_categories"
            cats = find_categories_fuzzy(message.text, dishes)
            registration_sessions['product']['categories'] = cats
            
            await bot.send_message(message.chat.id, f"Для продукта {message.text} автоматически определены следующие категории: {cats}. Их можно определить самому (напечатав через запятую и отправив), а можно оставить как есть (кнопка Пропустить)", reply_markup=back_skip_markup)

    @bot.message_handler(func=lambda message: registration_sessions.get(message.chat.id, {}).get("state") == "waiting_for_categories")
    @check_user_state()
    async def get_food_cats(message):
        if message.text == "Назад":
            await go_back(message)
            return
        else:
            if message.text != "Пропустить":
                registration_sessions["product"]["categories"] = message.text.split(",")
                await bot.send_message(message.chat.id, "Категории обновлены.")
            registration_sessions["state"] = "waiting_for_weight"
            
            await bot.send_message(message.chat.id, "Введите вес продукта (граммы) или нажмите 'Пропустить':", reply_markup=back_skip_markup)

    @bot.message_handler(func=lambda message: registration_sessions.get(message.chat.id, {}).get("state") == "waiting_for_weight")
    @check_user_state()
    async def get_food_weight(message):
        if message.text == "Назад":
            await go_back(message)
            return
        else:
            if message.text == "Пропустить":
                registration_sessions["state"] = "waiting_for_tare_weight"
                await bot.send_message(message.chat.id, "Введите вес тары (граммы) или нажмите 'Пропустить':", reply_markup=back_skip_markup)
                return

        try:
            weight = int(message.text)
            registration_sessions["product"]["weight"] = weight
            registration_sessions["state"] = "waiting_for_tare_weight"
            await bot.send_message(message.chat.id, "Введите вес тары (граммы) или нажмите 'Пропустить':", reply_markup=back_skip_markup)
        except ValueError:
            await bot.send_message(message.chat.id, "Введите корректный вес в граммах или нажмите 'Пропустить'.")

    @bot.message_handler(func=lambda message: registration_sessions.get(message.chat.id, {}).get("state") == "waiting_for_tare_weight")
    @check_user_state()
    async def get_food_tare_weight(message):
        if message.text == "Назад":
            await go_back(message)
            return
        else:
            if message.text == "Пропустить":
                registration_sessions["state"] = "waiting_for_source"
                await bot.send_message(message.chat.id, "Кто приготовил продукт? (по умолчанию 'Магазин') или нажмите 'Пропустить':", reply_markup=back_skip_markup)
                return

        try:
            tare_weight = int(message.text)
            registration_sessions["product"]["tare_weight"] = tare_weight
            registration_sessions["state"] = "waiting_for_source"
            await bot.send_message(message.chat.id, "Кто приготовил продукт? (по умолчанию 'Магазин') или нажмите 'Пропустить':", reply_markup=back_skip_markup)
        except ValueError:
            await bot.send_message(message.chat.id, "Введите корректный вес тары в граммах или нажмите 'Пропустить'.")

    @bot.message_handler(func=lambda message: registration_sessions.get(message.chat.id, {}).get("state") == "waiting_for_source")
    @check_user_state()
    async def get_food_source(message):
        if message.text == "Назад":
            await go_back(message)
            return
        else:
            if message.text == "Пропустить":
                registration_sessions["state"] = "waiting_for_manufacture_date"
                await bot.send_message(message.chat.id, "Выберите дату изготовления продукта на календаре или нажмите 'Пропустить':", reply_markup=calendar.create_calendar(calendar_1.prefix, datetime.datetime.now().year, datetime.datetime.now().month))
                return

        registration_sessions["product"]["source"] = message.text if message.text else "Магазин"
        registration_sessions["state"] = "waiting_for_manufacture_date"
        await bot.send_message(message.chat.id, "Выберите дату изготовления продукта на календаре или нажмите 'Пропустить':", reply_markup=calendar.create_calendar(calendar_1.prefix, datetime.datetime.now().year, datetime.datetime.now().month))
