import json
from utils import check_if_correct_data

new_products = "new_products.json"
fridge = 'fridge_data.json'
users = "users.json"


def write_json(file, data, need_check_datetime_format = False):
    try:
        # Преобразуем все даты в строки формата ISO ЕСЛИ НАДО
        if need_check_datetime_format:
            check_if_correct_data(data)
        # Сохраняем JSON
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка записи JSON: {e}")

def read_json(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Ошибка в json: {e}")
        return {}