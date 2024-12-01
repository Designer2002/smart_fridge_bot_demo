from telebot import types
def create_product_markup(product_id):
    from helpers import SEPARATOR
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(
        text="Зарегистрировать продукт",
        callback_data=f"register:" + SEPARATOR + product_id
    )
    markup.add(button)
    return markup


admin_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
admin_markup.add("Сообщение от датчика веса", "Рандомный продукт", "Начать интерактив")

start_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
start_markup.add("Новый продукт", "Найди просрочку", "Посоветуй вкусняшку", "Съесть продукт")

drop_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
drop_markup.add("1", "3", "5", "10", "15", "20")

back_skip_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
back_skip_markup.add("Назад", 'Пропустить')

check_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
check_markup.add("Сохранить", "Сброс")

eat_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
eat_markup.add("Съесть", "Съесть анонимно", "Назад")

def create_eating_markup(fridge_data):
    from data_loaders import eating_products
    markup = types.InlineKeyboardMarkup()
    for product in fridge_data:
        if product["name"] not in eating_products:  # Проверяем, свободен ли продукт
            markup.add(
                types.InlineKeyboardButton(
                    text=product["name"], 
                    callback_data=f"eat_{product['name']}"  # Уникальный идентификатор для каждой кнопки
                )
            )
    markup.add(
        types.InlineKeyboardButton(
            text="Назад", 
            callback_data="go_back"  # Идентификатор для кнопки "Назад"
        )
    )
    return markup