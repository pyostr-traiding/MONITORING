import json
from datetime import datetime, UTC


from API.schemas.position import PositionSchema
from app.schemas.kline import KlineUpdate
from conf.conf_redis import redis_server_data
from conf.config import redis_server


class BasePositionService:
    # ключ
    @staticmethod
    def _key(pos_id: int) -> str:
        return f"position:{pos_id}"

    async def get_position(self, pos_id: int) -> dict | None:
        raw = await redis_server_data.get(self._key(pos_id))
        return json.loads(raw) if raw else None

    async def set_position(self, pos_id: int, data: dict):
        data['dt'] = str(datetime.now(UTC))
        await redis_server_data.publish(
            'MONITORING',
            json.dumps(
                {
                    'id': pos_id,
                    'type': 'position',
                    'method': 'set',
                    'data': data,
                }
            )
        )
        await redis_server_data.set(self._key(pos_id), json.dumps(data))

    async def has_position(self, pos_id: int) -> bool:
        return await redis_server_data.exists(self._key(pos_id)) > 0

    async def process(self, position_dict: dict, trigger_data: dict) -> bool:
        position = PositionSchema.model_validate(position_dict)
        kline = KlineUpdate.model_validate(trigger_data)

        if position.category == "option":
            return await self._handle_option(position, kline)

        elif position.category == "spot":
            return await self._handle_spot(position, kline)

        print(f"[SKIP] Неизвестная категория: {position.category}")
        return False

    # -------- EXTREMUMS --------
    async def _load_existing_extremums(self, pos_uuid: str):
        keys = [
            f"extremum:position:{pos_uuid}:MIN",
            f"extremum:position:{pos_uuid}:MAX"
        ]

        results = await redis_server.mget(keys)

        def parse(val):
            try:
                return float(json.loads(val)["value"]) if val else None
            except:
                return None

        return parse(results[0]), parse(results[1])

    async def _update_extremum(self, pos_uuid: str, kind: str, value: float):
        key = f"extremum:position:{pos_uuid}:{kind}"
        data = {
            "value": value,
            "dt": datetime.now(UTC).strftime("%d-%m-%Y %H:%M:%S"),
        }
        await redis_server.set(key, json.dumps(data))

    async def _create_initial_extremums(self, pos_uuid: str, price: float):
        await self._update_extremum(pos_uuid, "MIN", price)
        await self._update_extremum(pos_uuid, "MAX", price)

    # must be overridden
    async def _handle_option(self, p, k): raise NotImplementedError
    async def _handle_spot(self, p, k): raise NotImplementedError
