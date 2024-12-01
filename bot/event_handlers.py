import asyncio
import datetime
import signal
from rx import operators as ops
from my_utils.database import read_json, write_json
from editors import edit_product_message
from my_utils.helpers import notify_and_delete_expired_product
from rx.subject import Subject, BehaviorSubject
import my_utils.data_loaders


shutdown_stream = Subject()
interactive_state = BehaviorSubject(my_utils.data_loaders.initial_state)
user_start_events = BehaviorSubject({})
products_stream = Subject()


# Поток событий для удаления устаревших продуктов
products_stream.pipe(
    ops.map(lambda event: (event[0], read_json(my_utils.data_loaders.config_data["events"]).get(event[0]))),  
    ops.filter(lambda event: event[1] is not None),
    ops.filter(lambda event: (datetime.datetime.now() - datetime.datetime.fromisoformat(event[1]["timestamp"])).total_seconds() > 86400),
).subscribe(
    lambda event: notify_and_delete_expired_product(event[0], event[1])
)

def initialize_streams(bot):
    # Поток событий для изменения сообщений
    products_stream.pipe(
    ops.filter(lambda event: event[1] == "in_progress"),
    ops.filter(lambda event: event[0] is not None),
    ).subscribe(lambda event: asyncio.run_coroutine_threadsafe(
        edit_product_message(bot, event[0], "UPD: Продукт уже регистрируют."),
        asyncio.get_event_loop()
    ))

    # Поток событий для завершённой регистрации
    products_stream.pipe(
        ops.filter(lambda event: event[1] == "registered"),
        ops.filter(lambda event: event[0] is not None),
    ).subscribe(lambda event: asyncio.run_coroutine_threadsafe(
        edit_product_message(bot, event[0], "✅ Продукт успешно зарегистрирован!"),
        asyncio.get_event_loop()
    ))

interactive_state.pipe(
    ops.distinct_until_changed()  # Реагируем только на изменение
).subscribe(
    lambda state: write_json(my_utils.data_loaders.config_data["interactive"], {"interactive_started" : state}))


#def handle_shutdown_signal(signal_number, frame):
    #shutdown_stream.on_next(True)
    
#shutdown_stream.pipe(
    #ops.distinct_until_changed()  # Реагируем только на изменение
#).subscribe(lambda _: write_json(my_utils.data_loaders.config_data["sessions_file"], data_loaders.registration_sessions))

#signal.signal(signal.SIGINT, handle_shutdown_signal)
#signal.signal(signal.SIGTERM, handle_shutdown_signal)