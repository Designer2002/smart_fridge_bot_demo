import datetime
import random
import traceback
from telebot.async_telebot import AsyncTeleBot
from data_loaders import create_dish_categories
from my_utils.helpers import add_new_weight_change, find_categories_fuzzy, find_user_with_correct_state, get_random_weight, notify_others_about_product, send_product_summary, start_adding_food, check_user_state, start_adding_food_msg
from markups import back_skip_markup, create_eating_markup, create_product_markup, start_markup, drop_markup, admin_markup, eat_markup
from my_utils.database import append_json, read_json, write_json
from callbacks import calendar, calendar_1
from event_handlers import products_stream, interactive_state



async def handle_messages(bot: AsyncTeleBot):
    from my_utils.data_loaders import config_data, dish_categories
    from my_utils.database import load_storage_tmp, save_storage_tmp
    from my_utils.helpers import SEPARATOR
    from data_loaders import eating_products
    @bot.message_handler(func=lambda message: message.text == "Назад")
    @check_user_state(bot)
    async def go_back(message):
        try:
            user_data=read_json(config_data["users"])
            previous_state = user_data[str(message.chat.id)].get("state", "start")
            token = user_data['state'].split(SEPARATOR)[-1]

            if previous_state.startswith("waiting_for_name"):
                user_data[str(message.chat.id)]["state"]="start"+SEPARATOR+token
                write_json(config_data["users"], user_data)
                await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=start_markup)
            elif previous_state.startswith("waiting_for_weight"):
                user_data[str(message.chat.id)]["state"]="waiting_for_name"+SEPARATOR+token
                write_json(config_data["users"], user_data)
                await bot.send_message(message.chat.id, "Введите название продукта:", reply_markup=back_skip_markup)
            elif previous_state.startswith("waiting_for_tare_weight"):
                user_data[str(message.chat.id)]["state"]="waiting_for_weight"+SEPARATOR+token
                write_json(config_data["users"], user_data)
                await bot.send_message(message.chat.id, "Введите вес продукта (граммы):", reply_markup=back_skip_markup)
            elif previous_state.startswith("waiting_for_source"):
                user_data[str(message.chat.id)]["state"]="waiting_for_tare_weight"+SEPARATOR+token
                write_json(config_data["users"], user_data)
                await bot.send_message(message.chat.id, "Введите вес тары (граммы):", reply_markup=back_skip_markup)
            elif previous_state.startswith("waiting_for_manufacture_date"):
                user_data[str(message.chat.id)]["state"]="waiting_for_source"
                write_json(config_data["users"], user_data)+SEPARATOR+token
                await bot.send_message(message.chat.id, "Кто приготовил продукт? (по умолчанию 'Магазин'):", reply_markup=back_skip_markup)
            elif previous_state.startswith("waiting_for_expiration_date"):
                user_data[str(message.chat.id)]["state"]="waiting_for_manufacture_date"+SEPARATOR+token
                write_json(config_data["users"], user_data)
                await bot.send_message(
                    message.chat.id, 
                    "Выберите дату изготовления продукта на календаре:\nВНИМАНИЕ! Календарь НЕ листается никуда! Нажимается только текущий месяц. В будущих версиях будет исправлено, но не в этой :(", 
                    reply_markup=calendar.create_calendar(calendar_1.prefix, datetime.datetime.now().year, datetime.datetime.now().month)
                )
            else:
                user_data[str(message.chat.id)]["state"]="start"+SEPARATOR+token
                write_json(config_data["users"], user_data)
                await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=start_markup)
            
        except Exception:
            user_data[str(message.chat.id)]["state"]="start"
            write_json(config_data["users"], user_data)
            await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=start_markup)

    @bot.message_handler(func=lambda message: message.text == "Добавить рандомный продукт" and str(message.from_user.id) == config_data["admin_id"])
    @check_user_state(bot)
    async def add_random_product(message):
        try:
            # Читаем список категорий из файла

            # Выбираем случайное блюдо
            random_dish_name, dish_data = random.choice(list(dish_categories.items()))

            # Генерируем случайные параметры
            random_weight = random.randint(200, 1000)  # Вес продукта в граммах
            tare_weight = 0  # Вес тары
            source = "Загадка..."  # Кто приготовил
            manufacture_date = datetime.date.today()+datetime.timedelta(days=random.randint(-7, 0)).isoformat()  # Сегодняшняя дата
            expiry_date = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()  # Плюс 5 дней

            # Формируем данные для добавления
            new_product = {
                "name": random_dish_name,
                "categories": dish_data["categories"],
                "weight": random_weight,
                "tare_weight": tare_weight,
                "source": source,
                "manufacture_date": manufacture_date,
                "expiry_date": expiry_date
            }

            # Читаем базу холодильника и добавляем новый продукт
            fridge_data = read_json(config_data["fridge"])
            fridge_data.append(new_product)
            write_json(config_data["fridge"], fridge_data)

            # Отправляем сообщение об успешном добавлении
            msg = (
                "✅ **Новый продукт добавлен в базу!**\n"
                f"📌 **Название:** {random_dish_name}\n"
                f"🍖 **Категория:** {dish_data['categories']}\n"
                f"⚖️ **Вес:** {random_weight} г\n"
                f"📦 **Вес тары:** {tare_weight} г\n"
                f"🏷️ **Источник (кто приготовил):** {source}\n"
                f"📅 **Дата изготовления:** {manufacture_date}\n"
                f"⏳ **Годен до:** {expiry_date}"
            )
            await bot.send_message(message.chat.id, msg, parse_mode="Markdown")

        except Exception as e:
            await bot.send_message(message.chat.id, f"Ошибка при добавлении продукта: {e}")

    @bot.message_handler(func=lambda message: message.text == "Сообщение от датчика веса")
    @check_user_state(bot)
    async def handle_weight_sensor(message):
        await bot.send_message(message.chat.id, "Сколько продуктов дропать?", reply_markup=drop_markup)
        # Чтение пользователей из JSON
        users = read_json(config_data["users"])
        
        # Проверяем, существует ли пользователь в JSON
        user_id = str(message.from_user.id)  # IDs в JSON сохранены как строки
        if user_id in users:
            # Обновляем состояние пользователя
            users[user_id]["state"] = "preparing_to_drop_food"
            write_json(config_data["users"], users)
            
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
            users = read_json(config_data["users"])
        
        # Проверяем, существует ли пользователь в JSON
            user_id = str(message.from_user.id)  # IDs в JSON сохранены как строки
            if user_id in users:
                # Обновляем состояние пользователя
                users[user_id]["state"] = "dropping_food"
                write_json(config_data["users"], users)
            
    @bot.message_handler(func=lambda message: find_user_with_correct_state(message.from_user.id, "dropping_food") and message.text.isdigit())
    @check_user_state(bot)
    async def drop_food(message):
        #print(message.chat.id, " -> message.chat.id")
        #print(message.from_user.id, " -> message.from_user.id")
        #print(message.message_id, " -> message.message.id")
        try:
            user_data = read_json(config_data['users'])
            user_ids = [int(user_id) for user_id in user_data.keys()]

            # Исключаем регистрирующего пользователя
            user_ids = [user_id for user_id in user_ids if user_id != message.from_user.id]
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
                message_to_reply = {}
                markup = create_product_markup(product_id)
                for u in user_ids:
                    sent_message = await bot.send_message(u, msg, reply_markup=markup)
                    message_id = sent_message.message_id  # Получаем ID сообщения
                    chat_id = u  # Получаем chat_id

                    # Сохраняем в базу данных или передаем в другую функцию

                    message_to_reply[u]={"chat_id" : chat_id,
                                         "message_id" : message_id,
                                         "product_id" : product_id}
                                         # Ваш метод сохранения
                    save_storage_tmp(message_to_reply)
                    
                

        except:
            print(traceback.print_exc())

    @bot.message_handler(func=lambda message: message.text == "Начать интерактив")
    @check_user_state(bot)
    async def start_interactive(message):
        interactive_state.on_next(True)  # Обновляем состояние потока
        await bot.send_message(message.chat.id, "Интерактив начался! Все желающие могут пользоваться ботом.", reply_markup=admin_markup)

    @bot.message_handler(func=lambda message: message.text == "Новый продукт" and read_json(config_data["users"])[str(message.chat.id)]["state"].startswith("start"))
    @check_user_state(bot)
    async def register_product(message):
        id = await start_adding_food_msg(bot, message)
        u = read_json(config_data['users'])
        u[str(message.chat.id)]['state'] = 'waiting_for_name'+SEPARATOR+id
        write_json(config_data['users'], u)

    @bot.message_handler(func=lambda message: message.text == "Найди просрочку")
    @check_user_state(bot)
    async def check_expiration(message):
        await bot.send_message(message.chat.id, "Эта функция пока не реализована. В будущем вы сможете увидеть продукты с истекающим сроком годности.")

    @bot.message_handler(func=lambda message: message.text == "Съесть продукт")
    @check_user_state(bot)
    async def eat_product_start(message):
        # Получаем данные из холодильника
        fridge_data = read_json(config_data["fridge"])
        if not fridge_data:
            await bot.send_message(message.chat.id, "В холодильнике нет продуктов. Кушать нечего!")
            return
        # Создаем клавиатуру с названиями продуктов
        markup = create_eating_markup(fridge_data)
        users = read_json(config_data["users"])
        users[str(message.chat.id)]["state"] = "eating"
        write_json(users)
        await bot.send_message(message.chat.id, "Выберите продукт, который хотите съесть:", reply_markup=markup)

    @bot.message_handler(func=lambda message: read_json(config_data['users'])[str(message.chat.id)]["state"] == "eating" and (message.text in [p["name"] for p in read_json(config_data["fridge_"])] or message.text == "Назад"))
    @check_user_state(bot)
    async def choose_product(message):
        if message.text == "Назад":
            await bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=start_markup)
            return

        product_name = message.text
        if product_name in eating_products:
            await bot.send_message(message.chat.id, f"Продукт {product_name} уже ест другой пользователь.")
            return

        # Занимаем продукт
        eating_products[product_name] = message.chat.id

        # Показываем варианты съедения

        await bot.send_message(
            message.chat.id,
            f"Вы выбрали {product_name}. Что хотите сделать?",
            reply_markup=eat_markup,
        )
    
    @bot.message_handler(func=lambda message: read_json(config_data['users'])[str(message.chat.id)]["state"] == "eating" and message.text in ["Съесть", "Съесть анонимно", "Назад"])
    @check_user_state(bot)
    async def eat_product_action(message):
        user_id = message.chat.id

        # Определяем продукт, связанный с пользователем
        product_name = next(
            (name for name, uid in eating_products.items() if uid == user_id), None
        )

        if not product_name:
            await bot.send_message(user_id, "Вы не выбрали продукт.")
            return

        if message.text == "Назад":
            del eating_products[product_name]  # Освобождаем продукт
            await bot.send_message(
                user_id, f"Продукт {product_name} снова доступен.", reply_markup=start_markup
            )
            return

        # Удаляем продукт из холодильника
        fridge_data = read_json(config_data["fridge"])
        fridge_data = [p for p in fridge_data if p["name"] != product_name]
        write_json(config_data["fridge"], fridge_data)

        # Формируем сообщение
        if message.text == "Съесть анонимно":
            notify_msg = f"Кто-то втихаря съедает {product_name}!"
        else:
            user_data = read_json(config_data["users"])
            user_name = user_data[str(user_id)]["name"]
            notify_msg = f"{user_name} съедает {product_name}!"

        # Уведомляем всех
        user_ids = [int(uid) for uid in user_data.keys() if int(uid) != user_id]
        for uid in user_ids:
            await bot.send_message(uid, notify_msg)

        # Освобождаем продукт
        del eating_products[product_name]

        await bot.send_message(
            user_id, f"Продукт {product_name} успешно съеден.", reply_markup=start_markup
        )
        users = read_json(config_data["users"])
        users[str(message.chat.id)]["state"] = "start"
        write_json(users)

    @bot.message_handler(func=lambda message: message.text == "Посоветуй вкусняшку")
    @check_user_state(bot)
    async def suggest_food(message):
        await bot.send_message(message.chat.id, "Эта функция пока не реализована. В будущем вы сможете увидеть рекомендации, что приготовить.")

    @bot.message_handler(func=lambda message: read_json(config_data["users"])[str(message.chat.id)]["state"].startswith("waiting_for_expiration_date"))
    @check_user_state(bot)
    async def get_food_expiration_date(message):
        product = read_json(config_data["users"])[str(message.chat.id)]["state"].split(SEPARATOR)[-1]
        if message.text == "Назад":
            await go_back(message)
            return
        else:
            if message.text == 'Пропустить':
                
                user_data = read_json(config_data["users"])
                s = load_storage_tmp()
                t = datetime.datetime.fromisoformat(s[product]["manufacture_date"]) + datetime.timedelta(days=3) 
                t = t.isoformat()
                s[product]['expiry_date'] = t
                save_storage_tmp(s)
                await send_product_summary(bot, message.chat.id, product)
                
                return

        try:
            days = int(message.text)
            
            user_data = read_json(config_data["users"])
            s = load_storage_tmp()
            t = datetime.datetime.fromisoformat(s[product]["manufacture_date"]) + datetime.timedelta(days=days) 
            t = t.isoformat()
            s[product]['expiry_date'] = t
            save_storage_tmp(s)
            await send_product_summary(bot, message.chat.id, product)
            
            
        except ValueError:
            await bot.send_message(message.chat.id, "Введите срок хранения в днях или нажмите 'Пропустить'.")


    @bot.message_handler(func=lambda message: read_json(config_data["users"])[str(message.chat.id)]["state"].startswith("final_check"))
    @check_user_state(bot)
    async def finalize_product(message):
        if message.text == "Сохранить":
            user_data = read_json(config_data['users'])
            if user_data:
                product = user_data[str(message.chat.id)]["state"].split(SEPARATOR)[-1]
                data = load_storage_tmp()[product]
                append_json(config_data["fridge"], data)
                user_data[str(message.chat.id)]["state"] = "start"
                await bot.send_message(message.chat.id, "Продукт успешно сохранен!", reply_markup=start_markup)
                e = read_json(config_data['events'])
                e[product]['state']="registered"
                products_stream.on_next((product, "registered", message.message_id) )
                await notify_others_about_product(bot, product,str(message.from_user.id))
                write_json(config_data['users'], user_data)
                s = load_storage_tmp()
                s[product] = {}
                save_storage_tmp(s)
        elif message.text == "Сброс":
            user_data = read_json(config_data['users'])
            user_data[str(message.chat.id)]["state"] = "start"
            await bot.send_message(message.chat.id, "Данные сброшены.", reply_markup=start_markup)
            write_json(config_data['users'], user_data)

    @bot.message_handler(func=lambda message: read_json(config_data["users"])[str(message.chat.id)]["state"].startswith("waiting_for_name"))
    @check_user_state(bot)
    async def get_food_name(message):
        product = read_json(config_data["users"])[str(message.chat.id)]["state"].split(SEPARATOR)[-1]
        user_data = read_json(config_data["users"])
        if message.text == 'Пропустить':
            bot.send_message(message.chat.id, "Название продукта нельзя пропустить. Пожалуйста, введите название.")
            return
        if message.text == "Назад":
            user_data[str(message.chat.id)]["state"]="start"
            write_json(config_data["users"], user_data)
            await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=start_markup)
            return 
        else:
            s = load_storage_tmp()
            s[product]["name"] = message.text
            user_data[str(message.chat.id)]["state"] = "waiting_for_categories"+SEPARATOR+product
            cats = find_categories_fuzzy(message.text, dish_categories)
            s[product]["categories"] = cats
            save_storage_tmp(s)
            write_json(config_data["users"], user_data)

            await bot.send_message(message.chat.id, f"Для продукта {message.text} автоматически определены следующие категории: {cats}. Их можно определить самому (напечатав через запятую и отправив), а можно оставить как есть (кнопка Пропустить)", reply_markup=back_skip_markup)

    @bot.message_handler(func=lambda message: read_json(config_data["users"])[str(message.chat.id)]["state"].startswith("waiting_for_categories"))
    @check_user_state(bot)
    async def get_food_cats(message):
        product = read_json(config_data["users"])[str(message.chat.id)]["state"].split(SEPARATOR)[-1]
        if message.text == "Назад":
            await go_back(message)
            return
        else:
            
            if message.text != 'Пропустить':
                s = load_storage_tmp()
                
                s[product]["categories"] = message.text.split(",")
                user_data = read_json(config_data["users"])
                user_data[str(message.chat.id)]["state"]="waiting_for_weight"+SEPARATOR+product
                write_json(config_data["users"], user_data)
                save_storage_tmp(s)
                await bot.send_message(message.chat.id, "Категории обновлены.")
                
            else:
                user_data = read_json(config_data["users"])
                
                user_data[str(message.chat.id)]["state"]="waiting_for_weight"+SEPARATOR+product
                write_json(config_data["users"], user_data)
                await bot.send_message(message.chat.id, "Введите вес продукта (граммы) или нажмите 'Пропустить':", reply_markup=back_skip_markup)
                

    @bot.message_handler(func=lambda message: read_json(config_data["users"])[str(message.chat.id)]["state"].startswith("waiting_for_weight"))
    @check_user_state(bot)
    async def get_food_weight(message):

        product = read_json(config_data["users"])[str(message.chat.id)]["state"].split(SEPARATOR)[-1]
        try_weight = None
        events = read_json(config_data['events'])
        
        try:
            try_weight=int(events[str(product)]["weight"])
        except Exception as e:
            try_weight = None
            print("Вес не найден. Кладмен мудак", e)
        if message.text == "Назад":
            await go_back(message)
            return
        else:
            if try_weight is not None:
                s = load_storage_tmp()
                user_data = read_json(config_data["users"])
                user_data[str(message.chat.id)]["state"] = "waiting_for_tare_weight"+SEPARATOR+product
                s[product]["weight"] = try_weight
                save_storage_tmp(s)
                write_json(config_data['users'],user_data)
                
                await bot.send_message(message.chat.id, "Введите вес тары (граммы) или нажмите 'Пропустить':", reply_markup=back_skip_markup)
                return
            elif message.text == 'Пропустить':
                s = load_storage_tmp()
                user_data = read_json(config_data["users"])
                user_data[str(message.chat.id)]["state"] = "waiting_for_tare_weight"+SEPARATOR+product
                s[product]["weight"] = 0
                save_storage_tmp(s)
                write_json(config_data['users'],user_data)
                
                await bot.send_message(message.chat.id, "Введите вес тары (граммы) или нажмите 'Пропустить':", reply_markup=back_skip_markup)
                return

        try:
            weight = int(message.text)
            s = load_storage_tmp()
            user_data = read_json(config_data["users"])
            user_data[str(message.chat.id)]["state"] = "waiting_for_tare_weight"+SEPARATOR+product
            write_json(config_data['users'],user_data)
            s[product]["weight"] = weight
            save_storage_tmp(s)
            await bot.send_message(message.chat.id, "Введите вес тары (граммы) или нажмите 'Пропустить':", reply_markup=back_skip_markup)
        except ValueError:
            await bot.send_message(message.chat.id, "Введите корректный вес в граммах или нажмите 'Пропустить'.")

    @bot.message_handler(func=lambda message: read_json(config_data["users"])[str(message.chat.id)]["state"].startswith("waiting_for_tare_weight"))
    @check_user_state(bot)
    async def get_food_tare_weight(message):
        product = read_json(config_data["users"])[str(message.chat.id)]["state"].split(SEPARATOR)[-1]
        if message.text == "Назад":
            await go_back(message)
            return
        else:
            if message.text == 'Пропустить':
                u = read_json(config_data['users'])
                u[str(message.chat.id)]["state"]="waiting_for_source"+SEPARATOR+product
                write_json(config_data['users'],u)
                await bot.send_message(message.chat.id, "Кто приготовил продукт? (по умолчанию 'Магазин') или нажмите 'Пропустить':", reply_markup=back_skip_markup)
                return

        try:
            tare_weight = int(message.text)
            s = load_storage_tmp()
            user_data = read_json(config_data["users"])
            user_data[str(message.chat.id)]["state"] = "waiting_for_source"+SEPARATOR+product
            write_json(config_data['users'],user_data)
            s[product]["tare_weight"] = tare_weight
            save_storage_tmp(s)
            await bot.send_message(message.chat.id, "Кто приготовил продукт? (по умолчанию 'Магазин') или нажмите 'Пропустить':", reply_markup=back_skip_markup)
        except ValueError:
            await bot.send_message(message.chat.id, "Введите корректный вес тары в граммах или нажмите 'Пропустить'.")

    @bot.message_handler(func=lambda message: read_json(config_data["users"])[str(message.chat.id)]["state"].startswith("waiting_for_source"))
    @check_user_state(bot)
    async def get_food_source(message):
        product = read_json(config_data["users"])[str(message.chat.id)]["state"].split(SEPARATOR)[-1]
        if message.text == "Назад":
            await go_back(message)
            return
        else:
            if message.text == 'Пропустить':
                user_data = read_json(config_data["users"])
                user_data[str(message.chat.id)]["state"] = "waiting_for_manufacture_date"+SEPARATOR+product
                write_json(config_data['users'],user_data)
                await bot.send_message(message.chat.id, "Выберите дату изготовления продукта на календаре:\nВНИМАНИЕ! Календарь НЕ листается никуда! Нажимается только текущий месяц. В будущих версиях будет исправлено, но не в этой :(", reply_markup=calendar.create_calendar(calendar_1.prefix, datetime.datetime.now().year, datetime.datetime.now().month))
                return

        s = load_storage_tmp()
        s[product]["source"] = message.text if message.text else 'Магазин'
        user_data = read_json(config_data["users"])
        user_data[str(message.chat.id)]["state"] = "waiting_for_manufacture_date"+SEPARATOR+product
        write_json(config_data['users'],user_data)
        save_storage_tmp(s)
        await bot.send_message(message.chat.id, "Выберите дату изготовления продукта на календаре:\nВНИМАНИЕ! Календарь НЕ листается никуда! Нажимается только текущий месяц. В будущих версиях будет исправлено, но не в этой :(", reply_markup=calendar.create_calendar(calendar_1.prefix, datetime.datetime.now().year, datetime.datetime.now().month))
