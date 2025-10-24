from app.services.order.services.option import OptionOrderService
from app.services.order.services.spot import SpotOrderService

class OrderRouter:
    def __init__(self):
        self.option_service = OptionOrderService()
        self.spot_service = SpotOrderService()

    async def process(self, position_dict: dict, trigger_data: dict) -> bool:
        category = position_dict.get("category")

        if category == "option":
            return await self.option_service.process(position_dict, trigger_data)
        elif category == "spot":
            return await self.spot_service.process(position_dict, trigger_data)
        else:
            print(f"[Router] Неизвестная категория: {category}")
            return False
