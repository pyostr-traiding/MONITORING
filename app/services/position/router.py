# app/services/position/router.py
import logging

from app.services.position.services.option import OptionPositionService
from app.services.position.services.spot import SpotPositionService

logger = logging.getLogger(__name__)


class PositionRouter:
    def __init__(self):
        self.option_service = OptionPositionService()
        self.spot_service = SpotPositionService()

    async def process(self, position_dict: dict, trigger_data: dict) -> bool:
        category = position_dict.get("category")
        logger.info(f"[Router] Категория: {category} | position_dict: {position_dict}")

        if category == "option":
            return await self.option_service.process(position_dict, trigger_data)
        elif category == "spot":
            return await self.spot_service.process(position_dict, trigger_data)
        else:
            logger.error(f"[Router] Неизвестная категория: {category} | position_dict: {position_dict}")
            return False
