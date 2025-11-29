import json
import logging
from datetime import datetime, UTC


from API.schemas.order import OrderSchema
from app.schemas.kline import KlineUpdate
from conf.conf_redis import redis_server_data, redis_server


logger = logging.getLogger(__name__)


class BaseOrderService:
    # ключ для хранения
    @staticmethod
    def _key(order_id: int) -> str:
        return f"order:{order_id}"

    async def get_order(self, order_id: int) -> dict | None:
        raw = await redis_server_data.get(self._key(order_id))
        return json.loads(raw) if raw else None

    async def set_order(self, order_id: int, data: dict):
        data['dt'] = str(datetime.now(UTC))
        await redis_server_data.publish(
            'MONITORING',
            json.dumps(
                {
                    'id': order_id,
                    'type': 'order',
                    'method': 'set',
                    'data': data,
                    'dt': str(datetime.now(UTC)),
                }
            )
        )
        await redis_server_data.set(self._key(order_id), json.dumps(data))

    async def has_order(self, order_id: int) -> bool:
        return await redis_server_data.exists(self._key(order_id)) > 0

    async def remove_order(self, order_id: int):
        await redis_server_data.publish(
            'MONITORING',
            json.dumps(
                {
                    'id': order_id,
                    'type': 'order',
                    'method': 'delete',
                }
            )
        )
        await redis_server_data.delete(self._key(order_id))

    async def process(self, order_dict: dict, trigger_data: dict) -> bool:
        order = OrderSchema.model_validate(order_dict)
        kline = KlineUpdate.model_validate(trigger_data)

        if order.category == "option":
            return await self._handle_option(order, kline)

        elif order.category == "spot":
            return await self._handle_spot(order, kline)

        logger.error(f"[SKIP] Неизвестная категория: {order.category}")
        return False

    # ---------- EXTREMUMS ----------
    async def _load_existing_extremums(self, pos_uuid: str):
        keys = [
            f"extremum:order:{pos_uuid}:MIN",
            f"extremum:order:{pos_uuid}:MAX",
        ]

        results = await redis_server.mget(keys)

        def parse(val):
            try:
                return float(json.loads(val)["value"]) if val else None
            except:
                return None

        return parse(results[0]), parse(results[1])

    async def _update_extremum(self, order_uuid: str, kind: str, value: float):
        key = f"extremum:order:{order_uuid}:{kind}"
        data = {
            "value": value,
            "dt": datetime.now(UTC).strftime("%d-%m-%Y %H:%M:%S"),
        }
        await redis_server.set(key, json.dumps(data))

    async def _create_initial_extremums(self, uuid: str, price: float):
        await self._update_extremum(uuid, "MIN", price)
        await self._update_extremum(uuid, "MAX", price)

    # must be overridden
    async def _handle_option(self, order, kline): raise NotImplementedError
    async def _handle_spot(self, order, kline): raise NotImplementedError
