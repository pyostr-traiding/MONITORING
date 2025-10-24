# app/services/position/router.py
from app.services.position.services.option import OptionPositionService
from app.services.position.services.spot import SpotPositionService

class PositionRouter:
    def __init__(self):
        self.option_service = OptionPositionService()
        self.spot_service = SpotPositionService()

    async def process(self, position_dict: dict, trigger_data: dict) -> bool:
        category = position_dict.get("category")

        if category == "option":
            return await self.option_service.process(position_dict, trigger_data)
        elif category == "spot":
            return await self.spot_service.process(position_dict, trigger_data)
        else:
            print(f"[Router] Неизвестная категория: {category}")
            return False
