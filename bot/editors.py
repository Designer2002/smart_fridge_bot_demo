import os


async def edit_product_message(bot, product_id, new_text):
    from database import read_json, load_storage_tmp
    from markups import create_product_markup
    from data_loaders import config_data
    import traceback

    print(f"Редактирование продукта с ID: {product_id}")

    # Загружаем временное хранилище
    s = load_storage_tmp()
    if not s:
        print("Временное хранилище пустое!")
        return

    # Читаем события
    e = read_json(config_data['events'])
    if str(product_id) not in e:
        print(f"Продукт с ID {product_id} не найден в 'events'")
        return

    pd = e[str(product_id)]
    print(f"Данные продукта: {pd}")

    # Получаем список пользователей
    user_data = read_json(config_data['users'])
    user_ids = [int(user_id) for user_id in user_data.keys()]

    # Исключаем администратора
    user_ids = [user_id for user_id in user_ids if user_id != int(os.getenv("ADMIN_ID"))]
    print(f"Пользователи для обновления: {user_ids}")

    if not user_ids:
        print(f"Для продукта {product_id} отсутствуют подходящие chat_id")
        return

    old_text = (
        "📦 ***Обнаружен новый продукт!***\n\n"
        f'📊 **Вес продукта:** {pd["weight"]} г\n'
        "❓ Кто-то положил это в холодильник, но мы пока не знаем, что это.\n\n"
        "👇 Нажмите кнопку ниже, чтобы зарегистрировать этот продукт."
    )

    # Редактируем сообщения для каждого пользователя
    for u in user_ids:
        try:
            if str(u) not in s or "message_id" not in s[str(u)]:
                print(f"Нет данных message_id для пользователя {u}")
                continue

            message_id = s[str(u)]['message_id']
            print(f"Редактируем сообщение для chat_id={u}, message_id={message_id}")

            await bot.edit_message_text(
                chat_id=u,
                message_id=message_id,
                text=f"{old_text}\n\n{new_text}",
                reply_markup=create_product_markup(product_id),
                parse_mode="Markdown"
            )
            print(f"Сообщение для chat_id={u} успешно обновлено")
        except Exception as e:
            traceback.print_exc()
            print(f"Ошибка при обновлении сообщения для chat_id={u}: {e}")
