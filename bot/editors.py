def edit_product_message(bot, product_id, new_text):
    from utils.database import read_json
    from markups import create_product_markup
    product = read_json().get(product_id)
    if product and product["message_id"]:
        bot.edit_message_text(
            chat_id=product["chat_id"],
            message_id=product["message_id"],
            text=new_text,
            reply_markup=create_product_markup(product_id)
        )