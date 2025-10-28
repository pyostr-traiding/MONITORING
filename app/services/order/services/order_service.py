import json
import logging
from typing import Dict, Any
from datetime import datetime, UTC

from conf.config import redis_server

from API.schemas.order import OrderSchema
from app.schemas.kline import KlineUpdate


# ==============================================================
# БАЗОВЫЙ КЛАСС
# ==============================================================

logger = logging.getLogger(__name__)


class BaseOrderService:
    def __init__(self):
        self._orders: Dict[int, Dict[str, Any]] = {}

    async def process(
        self,
        order_dict: dict,
        trigger_data: dict,
    ) -> bool:
        """
        Обработчик ордера — вызывается при каждом обновлении данных.
        """
        order = OrderSchema.model_validate(order_dict)
        kline = KlineUpdate.model_validate(trigger_data)

        # Маршрутизация по типу категории
        if order.category == "option":
            return await self._handle_option(order, kline)
        elif order.category == "spot":
            return await self._handle_spot(order, kline)
        else:
            logger.error(f"[SKIP] Неизвестная категория: {order.category}")
            return False

    # --- Методы, которые переопределяются в наследниках ---
    async def _handle_option(self, order: OrderSchema, kline: KlineUpdate) -> bool:
        raise NotImplementedError

    async def _handle_spot(self, order: OrderSchema, kline: KlineUpdate) -> bool:
        raise NotImplementedError

    # --- Общие для всех типов методы ---
    async def _load_existing_extremums(self, pos_uuid: str):
        keys = {
            "MIN": f"extremum:order:{pos_uuid}:MIN",
            "MAX": f"extremum:order:{pos_uuid}:MAX",
        }
        results = await redis_server.mget(keys.values())

        def parse(val):
            try:
                return float(json.loads(val)["value"]) if val else None
            except Exception:
                return None

        min_val = parse(results[0])
        max_val = parse(results[1])
        return min_val, max_val

    async def _update_extremum(self, order_uuid: str, kind: str, value: float):
        """
        Асинхронно обновляет экстремум (MIN или MAX) в Redis.
        """
        key = f"extremum:order:{order_uuid}:{kind}"
        data = {
            "value": value,
            "dt": datetime.now(UTC).strftime("%d-%m-%Y %H:%M:%S"),
        }
        await redis_server.set(key, json.dumps(data))
        print(f" -> Redis SET {key} = {data}")

    async def _create_initial_extremums(self, order_uuid: str, price: float):
        """
        Создаёт начальные экстремумы (MIN и MAX) в Redis.
        """
        await self._update_extremum(order_uuid, "MIN", price)
        await self._update_extremum(order_uuid, "MAX", price)