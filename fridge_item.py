import datetime


class FridgeItem:
    def __init__(self, id):
        self.id = id
        self.product_name = ""
        self.categories = []
        self.source = "Магазин"
        self.m_date = datetime.date.today()
        self.e_date = self.m_date + datetime.timedelta(days=3)
        self.weight = 0
        self.t_weight = 0