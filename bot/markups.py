from telebot import types
def create_product_markup(product_id):
    from my_utils.helpers import SEPARATOR
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
start_markup.add("Новый продукт", "Найди просрочку", "Посоветуй вкусняшку", "Удалить продукт")

drop_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
drop_markup.add("1", "3", "5", "10", "15", "20")

back_skip_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
back_skip_markup.add("Назад", "Пропустить")

check_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
check_markup.add("Сохранить", "Сброс")