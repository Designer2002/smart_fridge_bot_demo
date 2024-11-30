import my_utils.database
from rx.subject import Subject, BehaviorSubject
from telebot_calendar import Calendar, CallbackData, RUSSIAN_LANGUAGE
import my_utils.helpers

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

my_utils.helpers.create_config()
config_data = my_utils.helpers.read_config()

dish_categories = create_dish_categories(config_data['dishes'])

initial_state = my_utils.database.read_json(config_data['interactive']).get("interactive_started", False)


calendar = Calendar(language=RUSSIAN_LANGUAGE)
calendar_1 = CallbackData('calendar_1', 'action', 'year', 'month', 'day')

# Rx Stream для управления сигналами и событиями
shutdown_stream = Subject()

interactive_state = BehaviorSubject(initial_state)

# Поток событий для отслеживания нажатий команды /start
user_start_events = BehaviorSubject({})
products_stream = Subject()



