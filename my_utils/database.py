import json
import threading
import my_utils.helpers
LOCK = threading.Lock()

def write_json(file, data, need_check_datetime_format = False):
    try:
        # Преобразуем все даты в строки формата ISO ЕСЛИ НАДО
        if need_check_datetime_format:
            my_utils.helpers.check_if_correct_data(data)
        # Сохраняем JSON
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка записи JSON: {e}")

def read_json(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):  # Проверяем, что загруженные данные — это словарь
                return data
            else:
                print(f"Ошибка: содержимое файла {file} не является JSON-объектом. Может, файл пуст")
                return {}
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Ошибка в json: {e}")
        return {}

def set_user_state(file, user_id, state):
    states = read_json(file)
    if user_id not in states:
        states[user_id] = {"enabled": True, "state": state}  # Создаём начальную структуру
    else:
        states[user_id]["state"] = state  # Обновляем состояние пользователя
    write_json(file, states)

def get_user_state(file, user_id):
    states = read_json(file)
    user_data = states.get(str(user_id))  # Используем строковое представление user_id
    if user_data:
        return user_data.get("state")
    return None

def clear_user_state(file,user_id):
    states = read_json(file)
    if str(user_id) in states:
        del states[str(user_id)]
        write_json(file, states)

# Загружаем сессии при старте
def load_storage_tmp():
    from data_loaders import config_data
    return read_json(config_data["storage_tmp"]) 

def save_storage_tmp(data):
    from data_loaders import config_data
    write_json(config_data["storage_tmp"], data)