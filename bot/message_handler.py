import datetime
import traceback
from telebot.async_telebot import AsyncTeleBot
from my_utils.helpers import add_new_weight_change, find_categories_fuzzy, find_user_with_correct_state, get_random_weight, notify_others_about_product, send_product_summary, start_adding_food, check_user_state
from markups import back_skip_markup, create_product_markup, start_markup, drop_markup, admin_markup
from my_utils.database import read_json, write_json
from callbacks import calendar, calendar_1
from event_handlers import products_stream, interactive_state



async def handle_messages(bot: AsyncTeleBot):
    from my_utils.data_loaders import config_data
    from my_utils.database import load_storage_tmp, save_storage_tmp
    from my_utils.helpers import SEPARATOR
    @bot.message_handler(func=lambda message: message.text == "Назад")
    @check_user_state(bot)
    async def go_back(message):
        try:
            user_data = read_json(config_data['users'])[str(message.chat.id)]
            previous_state = user_data.get("state", "start")

            if previous_state == "waiting_for_name":
                user_data['state']="start"
                write_json(config_data['users'], user_data)
                await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=start_markup)
            elif previous_state == "waiting_for_weight":
                user_data['state']="waiting_for_name"
                write_json(config_data['users'], user_data)
                await bot.send_message(message.chat.id, "Введите название продукта:", reply_markup=back_skip_markup)
            elif previous_state == "waiting_for_tare_weight":
                user_data['state']="waiting_for_weight"
                write_json(config_data['users'], user_data)
                await bot.send_message(message.chat.id, "Введите вес продукта (граммы):", reply_markup=back_skip_markup)
            elif previous_state == "waiting_for_source":
                user_data['state']="waiting_for_tare_weight"
                write_json(config_data['users'], user_data)
                await bot.send_message(message.chat.id, "Введите вес тары (граммы):", reply_markup=back_skip_markup)
            elif previous_state == "waiting_for_manufacture_date":
                user_data['state']="waiting_for_source"
                write_json(config_data['users'], user_data)
                await bot.send_message(message.chat.id, "Кто приготовил продукт? (по умолчанию 'Магазин'):", reply_markup=back_skip_markup)
            elif previous_state == "waiting_for_expiration_date":
                user_data['state']="waiting_for_manufacture_date"
                write_json(config_data['users'], user_data)
                await bot.send_message(
                    message.chat.id, 
                    "Выберите дату изготовления продукта на календаре:", 
                    reply_markup=calendar.create_calendar(calendar_1.prefix, datetime.datetime.now().year, datetime.datetime.now().month)
                )
            else:
                user_data['state']="start"
                write_json(config_data['users'], user_data)
                await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=start_markup)
            
        except Exception:
            user_data['state']="start"
            write_json(config_data['users'], user_data)
            await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=start_markup)

    @bot.message_handler(func=lambda message: message.text == "Рандомный продукт")
    @check_user_state(bot)
    async def handle_random_product(message):
        await bot.send_message(message.chat.id, "Вот случайный продукт из вашего холодильника!")

    @bot.message_handler(func=lambda message: message.text == "Сообщение от датчика веса")
    @check_user_state(bot)
    async def handle_weight_sensor(message):
        await bot.send_message(message.chat.id, "Сколько продуктов дропать?", reply_markup=drop_markup)
        # Чтение пользователей из JSON
        users = read_json(config_data['users'])
        
        # Проверяем, существует ли пользователь в JSON
        user_id = str(message.from_user.id)  # IDs в JSON сохранены как строки
        if user_id in users:
            # Обновляем состояние пользователя
            users[user_id]['state'] = "preparing_to_drop_food"
            write_json(config_data['users'], users)
            
        else:
            await bot.send_message(message.chat.id, "Только фиг вам в обе руки: пользователь не найден!")
    
    @bot.message_handler(func=lambda message: find_user_with_correct_state(message.from_user.id, "preparing_to_drop_food"))
    @check_user_state(bot)
    def register_product(message):
        try:
            num = int(message.text)
        except:
            pass
        finally:
            users = read_json(config_data['users'])
        
        # Проверяем, существует ли пользователь в JSON
            user_id = str(message.from_user.id)  # IDs в JSON сохранены как строки
            if user_id in users:
                # Обновляем состояние пользователя
                users[user_id]['state'] = "dropping_food"
                write_json(config_data['users'], users)
            
    @bot.message_handler(func=lambda message: find_user_with_correct_state(message.from_user.id, "dropping_food") and message.text.isdigit())
    @check_user_state(bot)
    async def drop_food(message):
        #print(message.chat.id, ' -> message.chat.id')
        #print(message.from_user.id, ' -> message.from_user.id')
        #print(message.message_id, ' -> message.message.id')
        try:
            num = int(message.text)
            for _ in range(num):
                random_weight = get_random_weight(100,1100)
                product_id = add_new_weight_change(random_weight, message.chat.id, message.message_id)
                msg = (
                "📦 ***Обнаружен новый продукт!***\n\n"
                f"📊 **Вес продукта:** {random_weight} г\n"
                "❓ Кто-то положил это в холодильник, но мы пока не знаем, что это.\n\n"
                "👇 Нажмите кнопку ниже, чтобы зарегистрировать этот продукт."
            )
                markup = create_product_markup(product_id)
                await bot.send_message(
                    message.chat.id,
                    msg,
                    reply_markup=markup,
                    parse_mode="Markdown"
                )

        except:
            print(traceback.print_exc())

    @bot.message_handler(func=lambda message: message.text == "Начать интерактив")
    @check_user_state(bot)
    async def start_interactive(message):
        interactive_state.on_next(True)  # Обновляем состояние потока
        await bot.send_message(message.chat.id, "Интерактив начался! Все желающие могут пользоваться ботом.", reply_markup=admin_markup)

    @bot.message_handler(func=lambda message: message.text == "Новый продукт" and find_user_with_correct_state(message.from_user.id, "adding_food"))
    @check_user_state(bot)
    async def register_product(message):
        await start_adding_food(bot, message)

    @bot.message_handler(func=lambda message: message.text == "Найди просрочку")
    @check_user_state(bot)
    async def check_expiration(message):
        await bot.send_message(message.chat.id, "Эта функция пока не реализована. В будущем вы сможете увидеть продукты с истекающим сроком годности.")

    @bot.message_handler(func=lambda message: message.text == "Удалить продукт")
    @check_user_state(bot)
    async def delete_product(message):
        await bot.send_message(message.chat.id, "Функция удаления продукта находится в разработке.")

    @bot.message_handler(func=lambda message: message.text == "Посоветуй вкусняшку")
    @check_user_state(bot)
    async def suggest_food(message):
        await bot.send_message(message.chat.id, "Эта функция пока не реализована. В будущем вы сможете увидеть рекомендации, что приготовить.")

    @bot.message_handler(func=lambda message: read_json(config_data['users'])[str(message.chat.id)]['state'].startswith("waiting_for_expiration_date"))
    @check_user_state(bot)
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


    @bot.message_handler(func=lambda message: read_json(config_data['users'])[str(message.chat.id)]['state'].startswith("final_check"))
    @check_user_state(bot)
    async def finalize_product(message):
        if message.text == "Сохранить":
            user_data = user_state_manager.get_current_state(message.chat.id)
            if user_data:
                product = user_data["product"]
                data = read_json()
                data.append(product)
                write_json(config_data['fridge'], data, True)
                await bot.send_message(message.chat.id, "Продукт успешно сохранен!", reply_markup=start_markup)
                products_stream.on_next(read_json(config_data['users'])[str(message.chat.id)].get("product_id"), "registered")
        elif message.text == "Сброс":
            await bot.send_message(message.chat.id, "Данные сброшены.", reply_markup=start_markup)


    @bot.message_handler(func=lambda message: read_json(config_data['users'])[str(message.chat.id)]['state'].startswith("registering_product"))
    async def finalize_registration(message):
        product_id = registration_sessions[message.chat.id].get("product_id")
        product = registration_sessions

        if product and product["user_id"] == message.from_user.id:
            # Завершаем регистрацию
            product["status"] = "registered"
            write_json(config_data['new_products'], product["status"])
            products_stream.on_next((product_id, "registered"))

            # Отправляем пользователю сообщение о завершении
            await bot.send_message(message.chat.id, "Продукт успешно зарегистрирован!")

            # Уведомляем всех остальных
            await notify_others_about_product(product_id, message.from_user.id)
        else:
            await bot.send_message(message.chat.id, "Ошибка регистрации. Попробуйте снова.")

    @bot.message_handler(func=lambda message: read_json(config_data['users'])[str(message.chat.id)]['state'].startswith("waiting_for_name"))
    @check_user_state(bot)
    async def get_food_name(message):
        product = read_json(config_data['users'])[str(message.chat.id)]['state'].split(SEPARATOR)[-1]
        user_data = read_json(config_data['users'])[str(message.chat.id)]
        if message.text == "Пропустить":
            bot.send_message(message.chat.id, "Название продукта нельзя пропустить. Пожалуйста, введите название.")
            return
        if message.text == "Назад":
            user_data['state']="start"
            write_json(config_data['users'], user_data)
            await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=start_markup)
            return 
        else:
            s = load_storage_tmp()
            s[product]["name"] = message.text
            user_data['state'] = "waiting_for_categories"
            cats = find_categories_fuzzy(message.text, config_data['dishes'])
            s[product]['categories'] = cats
            save_storage_tmp(s)
            write_json(config_data['users'], user_data)

            await bot.send_message(message.chat.id, f"Для продукта {message.text} автоматически определены следующие категории: {cats}. Их можно определить самому (напечатав через запятую и отправив), а можно оставить как есть (кнопка Пропустить)", reply_markup=back_skip_markup)

    @bot.message_handler(func=lambda message: read_json(config_data['users'])[str(message.chat.id)]['state'].startswith("waiting_for_categories"))
    @check_user_state(bot)
    async def get_food_cats(message):
        if message.text == "Назад":
            await go_back(message)
            return
        else:
            if message.text != "Пропустить":
                my_utils.data_loaders.storage_tmp["product"]["categories"] = message.text.split(",")
                await bot.send_message(message.chat.id, "Категории обновлены.")
                user_data = read_json(config_data['users'])[str(message.chat.id)]
                user_data['state']="waiting_for_weight"
                write_json(config_data['users'], user_data)
            
            await bot.send_message(message.chat.id, "Введите вес продукта (граммы) или нажмите 'Пропустить':", reply_markup=back_skip_markup)

    @bot.message_handler(func=lambda message: my_utils.data_loaders.storage_tmp.get(message.from_user.id, {}).get('state') == "waiting_for_tare_weight")
    @check_user_state(bot)
    async def get_food_weight(message):
        if message.text == "Назад":
            await go_back(message)
            return
        else:
            if message.text == "Пропустить":
                user_state_manager.set_state(message.chat.id, "waiting_for_tare_weight")
                await bot.send_message(message.chat.id, "Введите вес тары (граммы) или нажмите 'Пропустить':", reply_markup=back_skip_markup)
                return

        try:
            weight = int(message.text)
            registration_sessions["product"]["weight"] = weight
            user_state_manager.set_state(message.chat.id, "waiting_for_tare_weight")
            await bot.send_message(message.chat.id, "Введите вес тары (граммы) или нажмите 'Пропустить':", reply_markup=back_skip_markup)
        except ValueError:
            await bot.send_message(message.chat.id, "Введите корректный вес в граммах или нажмите 'Пропустить'.")

    @bot.message_handler(func=lambda message: storage_tmp.get(message.from_user.id, {}).get('state') == "waiting_for_weight")
    @check_user_state(bot)
    async def get_food_tare_weight(message):
        if message.text == "Назад":
            await go_back(message)
            return
        else:
            if message.text == "Пропустить":
                user_state_manager.set_state(message.chat.id, "waiting_for_source")
                await bot.send_message(message.chat.id, "Кто приготовил продукт? (по умолчанию 'Магазин') или нажмите 'Пропустить':", reply_markup=back_skip_markup)
                return

        try:
            tare_weight = int(message.text)
            registration_sessions["product"]["tare_weight"] = tare_weight
            user_state_manager.set_state(message.chat.id, "waiting_for_source")
            await bot.send_message(message.chat.id, "Кто приготовил продукт? (по умолчанию 'Магазин') или нажмите 'Пропустить':", reply_markup=back_skip_markup)
        except ValueError:
            await bot.send_message(message.chat.id, "Введите корректный вес тары в граммах или нажмите 'Пропустить'.")

    @bot.message_handler(func=lambda message: storage_tmp.get(message.from_user.id, {}).get('state') == "waiting_for_source")
    @check_user_state(bot)
    async def get_food_source(message):
        if message.text == "Назад":
            await go_back(message)
            return
        else:
            if message.text == "Пропустить":
                user_state_manager.set_state(message.chat.id, "waiting_for_manufacture_date")
                await bot.send_message(message.chat.id, "Выберите дату изготовления продукта на календаре или нажмите 'Пропустить':", reply_markup=calendar.create_calendar(calendar_1.prefix, datetime.datetime.now().year, datetime.datetime.now().month))
                return

        registration_sessions["product"]["source"] = message.text if message.text else "Магазин"
        user_state_manager.set_state(message.chat.id, "waiting_for_manufacture_date")
        await bot.send_message(message.chat.id, "Выберите дату изготовления продукта на календаре или нажмите 'Пропустить':", reply_markup=calendar.create_calendar(calendar_1.prefix, datetime.datetime.now().year, datetime.datetime.now().month))
