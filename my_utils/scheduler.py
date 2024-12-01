from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import date
from database import read_json, write_json

def run_scheduler(bot):
    scheduler = AsyncIOScheduler()

    async def check_expired_products():
        data = read_json("data/fridge_data.json")
        expired_products = [
            p for p in data if "expiry_date" in p and date.fromisoformat(p["expiry_date"]) < date.today()
        ]
        for product in expired_products:
            await bot.send_message(
                product["chat_id"], 
                f'Продукт {product["name"]} просрочен! Удаляем.'
            )
            data.remove(product)
        write_json("data/fridge_data.json", data)

    scheduler.add_job(check_expired_products, "interval", hours=8)
    scheduler.start()