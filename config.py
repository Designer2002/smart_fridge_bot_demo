from rx.subject import Subject, BehaviorSubject
from telebot_calendar import Calendar, CallbackData, RUSSIAN_LANGUAGE
from utils.data_loaders import initial_state

new_products = "data/new_products.json"
fridge = 'data/fridge_data.json'
users = "data/users.json"
dishes = "data/dishes.txt"
interactive = "state.json"
sessions_file = "registration_sessions.json"

admin_id = '699861867'

bot_token = "7223871421:AAG2IKwKcGALr5UUYbs15LI9ndd8xpS1FpQ"
calendar = Calendar(language=RUSSIAN_LANGUAGE)
calendar_1 = CallbackData('calendar_1', 'action', 'year', 'month', 'day')


# Временное хранилище для незавершенных регистраций
registration_sessions = {}

# Rx Stream для управления сигналами и событиями
shutdown_stream = Subject()

interactive_state = BehaviorSubject(initial_state)

# Поток событий для отслеживания нажатий команды /start
user_start_events = BehaviorSubject({})
products_stream = Subject()

