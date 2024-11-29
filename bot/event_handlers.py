import datetime
import signal
from rx import operators as ops
from utils.database import read_json, write_json
import config
from editors import edit_product_message
from utils.helpers import notify_and_delete_expired_product
from rx.subject import Subject, BehaviorSubject
import utils.data_loaders
import message_handler


shutdown_stream = Subject()
interactive_state = BehaviorSubject(utils.data_loaders.initial_state)
user_start_events = BehaviorSubject({})
products_stream = Subject()

# Поток событий для удаления устаревших продуктов
products_stream.pipe(
    ops.map(lambda event: (event[0], read_json(config.new_products).get(event[0]))),  
    ops.filter(lambda event: event[1] is not None),
    ops.filter(lambda event: (datetime.datetime.now() - datetime.datetime.fromisoformat(event[1]["timestamp"])).total_seconds() > 86400),
).subscribe(
    lambda event: notify_and_delete_expired_product(event[0], event[1])
)

# Поток событий для изменения сообщений
products_stream.pipe(
    ops.filter(lambda event: event[1] == "in_progress"),
    ops.filter(lambda event: event[0] is not None),
).subscribe(lambda event: edit_product_message(event[0], "UPD: Продукт уже регистрируют."))

# Поток событий для завершённой регистрации
products_stream.pipe(
    ops.filter(lambda event: event[1] == "registered"),
    ops.filter(lambda event: event[0] is not None),
).subscribe(lambda event: edit_product_message(event[0], "✅ Продукт успешно зарегистрирован!"))

interactive_state.pipe(
    ops.distinct_until_changed()  # Реагируем только на изменение
).subscribe(
    lambda state: write_json(utils.data_loaders.config_data['interactive'], f"interactive_started : {state}")
)

def handle_shutdown_signal(signal_number, frame):
    shutdown_stream.on_next(True)
    
shutdown_stream.pipe(
    ops.distinct_until_changed()  # Реагируем только на изменение
).subscribe(lambda _: write_json(utils.data_loaders.config_data['sessions_file'], message_handler.registration_sessions))

signal.signal(signal.SIGINT, handle_shutdown_signal)
signal.signal(signal.SIGTERM, handle_shutdown_signal)