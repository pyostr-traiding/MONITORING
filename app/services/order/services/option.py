# ==============================================================
# ФЬЮЧЕРСЫ / ОПЦИОНЫ
# ==============================================================
import logging
from decimal import Decimal

from API.orders import api_get_order, api_change_status_order, api_close_order
from API.schemas.order import OrderSchema

from app.schemas.kline import KlineUpdate
from app.services.order.services.order_service import BaseOrderService

logger = logging.getLogger(__name__)

class OptionOrderService(BaseOrderService):

    async def _handle_option(self, order: OrderSchema, kline: KlineUpdate) -> bool:
        current_price = float(kline.data.data.c)
        if not await self.has_order(order.id):   # <--- await
            api_order = await api_get_order(uuid=order.uuid)
            if api_order is None:
                return False
            if api_order is False:
                logger.info(f'Отмена статусом: {order}')
                return True
            result_accept = await api_change_status_order(
                uuid=order.uuid,
                status='monitoring'
            )
            if not result_accept:
                return False
            await self._add_new_option_order(order, kline)
            return False

        await self._update_option_extremums(order.id, current_price)
        result = await self.calculation_profit(order, kline)
        return result

    async def _add_new_option_order(self, order: OrderSchema, kline: KlineUpdate):
        order_uuid = order.uuid
        min_val, max_val = await self._load_existing_extremums(order_uuid)
        current_price = float(kline.data.data.c)
        if min_val is None or max_val is None:
            min_val = max_val = current_price
            await self._update_extremum(order_uuid, "MIN", min_val)
            await self._update_extremum(order_uuid, "MAX", max_val)
            logger.info(f"[INIT] Установлены экстремумы по текущему курсу: {current_price}")
        else:
            logger.info(f"[LOAD] Найдены экстремумы в Redis: MIN={min_val}, MAX={max_val}")

        await self.set_order(order.id, {   # <--- await
            "uuid": order_uuid,
            "symbol": order.symbol_name,
            "side": order.side,
            "price_entry": float(order.price),
            "max_price": float(max_val),
            "min_price": float(min_val),
        })
        logger.info(f"[NEW] {order.symbol_name} ({order.side}) по {order.price}")

    async def _update_option_extremums(self, order_id: int, current_price: float):
        order = await self.get_order(order_id)  # <--- await
        if not order:
            logger.error(f"Ордер {order_id} не найден в redis для обновления экстремумов.")
            return
        order_uuid = order["uuid"]
        updated = False

        if current_price > order["max_price"]:
            order["max_price"] = current_price
            await self._update_extremum(order_uuid, "MAX", current_price)
            logger.info(f"[UPDATE] Новый MAX = {current_price}")
            updated = True

        if current_price < order["min_price"]:
            order["min_price"] = current_price
            await self._update_extremum(order_uuid, "MIN", current_price)
            logger.info(f"[UPDATE] Новый MIN = {current_price}")
            updated = True

        if updated:
            await self.set_order(order_id, order)  # <--- await
            logger.info(
                f"[EXTREMUMS] {order['symbol']} ({order['side']}) "
                f"MIN={order['min_price']:.2f} | MAX={order['max_price']:.2f}"
            )

    async def calculation_profit(
            self,
            order: OrderSchema,
            kline: KlineUpdate
    ):
        """
        Рассчитаем, достиг ли курс нужной отметки
        """
        current_price = Decimal(kline.data.data.c)
        if order.side == 'buy':
            if current_price >= Decimal(order.target_rate):
                result = await api_close_order(uuid=order.uuid, rate=current_price)
                return result
            return False
        if order.side == 'sell':
            if current_price <=  Decimal(order.target_rate):
                result = await api_close_order(uuid=order.uuid, rate=current_price)
                return result
            return False




