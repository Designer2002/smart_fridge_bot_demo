async def edit_product_message(bot, product_id, new_text, msg_id):
    from my_utils.database import read_json
    from markups import create_product_markup
    from my_utils.data_loaders import config_data
    # Чтение JSON
    events = read_json(config_data["events"])
    
    # Проверяем, существует ли продукт
    if events and product_id in events:
        product_data = events[product_id]
        
        # Получаем chat_id и предполагаемый message_id
        chat_id = int(product_data.get("chat_id"))
        message_id = msg_id

        
        if not chat_id or not message_id:
            raise ValueError(f"Для продукта {product_id} отсутствует chat_id или message_id")
        
        # Пытаемся обновить сообщение
        try:
            old_text = (
                "📦 ***Обнаружен новый продукт!***\n\n"
                f'📊 **Вес продукта:** {product_data["weight"]} г\n'
                "❓ Кто-то положил это в холодильник, но мы пока не знаем, что это.\n\n"
                "👇 Нажмите кнопку ниже, чтобы зарегистрировать этот продукт.")
            
            # Редактируем текст сообщения
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"{old_text}\n\n{new_text}",
                reply_markup=create_product_markup(product_id),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Ошибка при обновлении сообщения: {e}")
    else:
        print(f"Продукт с ID {product_id} не найден в events")
