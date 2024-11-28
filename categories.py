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

dishes = 'dishes.txt'  # Путь к вашему файлу с данными