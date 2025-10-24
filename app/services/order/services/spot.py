# ==============================================================
# СПОТ
# ==============================================================
from API.schemas.order import OrderSchema
from app.services.order.services.order_service import BaseOrderService


class SpotOrderService(BaseOrderService):
    async def _handle_spot(self, order: OrderSchema, current_price: float) -> bool:
        """
        Обработка спотовой позиции.
        Пока реализуем как заглушку.
        """
        print(f"[SPOT:ORDER] {order.symbol_name} — обработка спота пока не реализована.")
        return False