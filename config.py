from rx.subject import Subject
from telebot_calendar import Calendar, CallbackData, RUSSIAN_LANGUAGE

from categories import create_dish_categories, dishes


admin_id = '699861867'

bot_token = "7223871421:AAG2IKwKcGALr5UUYbs15LI9ndd8xpS1FpQ"
calendar = Calendar(language=RUSSIAN_LANGUAGE)
calendar_1 = CallbackData('calendar_1', 'action', 'year', 'month', 'day')

USER_STATE = {}  # Хранит данные о состоянии пользователя

products_stream = Subject()

dish_categories = create_dish_categories(dishes)