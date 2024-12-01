import json
import helpers


def write_json(file, data, need_check_datetime_format = False):
    try:
        # Преобразуем все даты в строки формата ISO ЕСЛИ НАДО
        if need_check_datetime_format:
            helpers.check_if_correct_data(data)
        # Сохраняем JSON
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка записи JSON: {e}")

def append_json(file, new_data):
    try:
        # Читаем существующие данные из файла
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = []  # Если файл не найден, начинаем с пустого списка

        # Убедимся, что данные представляют собой массив
        if not isinstance(data, list):
            raise ValueError("Существующий JSON должен быть массивом")

        # Добавляем новые данные
        if isinstance(new_data, list):
            data.extend(new_data)  # Если новые данные — список, расширяем массив
        else:
            data.append(new_data)  # Если новые данные — объект, добавляем в массив

        # Записываем обратно в файл
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка дописывания в JSON: {e}")

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
    
def read_json_array_fridge(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            d = json.load(f)
            if not isinstance(d, list):
                d = json.loads(d)
            return d
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Ошибка в json: {e}")
        return []

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