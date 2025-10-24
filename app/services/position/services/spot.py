# ==============================================================
# СПОТ
# ==============================================================
from API.schemas.position import PositionSchema
from app.services.position.services.position_service import BasePositionService


class SpotPositionService(BasePositionService):
    async def _handle_spot(self, position: PositionSchema, current_price: float) -> bool:
        """
        Обработка спотовой позиции.
        Пока реализуем как заглушку.
        """
        print(f"[SPOT:Position] {position.symbol_name} — обработка спота пока не реализована.")
        return False