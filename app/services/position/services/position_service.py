import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, UTC

from config import redis_server
from API.schemas.position import PositionSchema
from app.schemas.kline import KlineUpdate


# ==============================================================
# БАЗОВЫЙ КЛАСС
# ==============================================================

class BasePositionService:
    def __init__(self):
        self._positions: Dict[int, Dict[str, Any]] = {}

    async def process(
        self,
        position_dict: dict,
        trigger_data: dict,
    ) -> bool:
        """
        Обработчик позиции — вызывается при каждом обновлении данных.
        """
        position = PositionSchema.model_validate(position_dict)
        kline = KlineUpdate.model_validate(trigger_data)

        # Маршрутизация по типу категории
        if position.category == "option":
            return await self._handle_option(position, kline)
        elif position.category == "spot":
            return await self._handle_spot(position, kline)
        else:
            print(f"[SKIP] Неизвестная категория: {position.category}")
            return False

    # --- Методы, которые переопределяются в наследниках ---
    async def _handle_option(self, position: PositionSchema, kline: KlineUpdate) -> bool:
        raise NotImplementedError

    async def _handle_spot(self, position: PositionSchema, kline: KlineUpdate) -> bool:
        raise NotImplementedError

    # --- Общие для всех типов методы ---
    async def _load_existing_extremums(self, pos_uuid: uuid.UUID) -> tuple[Optional[float], Optional[float]]:
        """
        Проверяет наличие экстремумов (MIN и MAX) в Redis.
        Возвращает (min, max) или (None, None)
        """
        keys = {
            "MIN": f"extremum:position:{pos_uuid}:MIN",
            "MAX": f"extremum:position:{pos_uuid}:MAX",
        }

        results = await redis_server.mget(keys.values())
        min_val, max_val = None, None

        if results[0]:
            try:
                min_val = json.loads(results[0])["value"]
            except (KeyError, json.JSONDecodeError):
                pass

        if results[1]:
            try:
                max_val = json.loads(results[1])["value"]
            except (KeyError, json.JSONDecodeError):
                pass

        return min_val, max_val

    async def _update_extremum(self, pos_uuid: uuid.UUID, kind: str, value: float):
        """
        Асинхронно обновляет экстремум (MIN или MAX) в Redis.
        """
        key = f"extremum:position:{pos_uuid}:{kind}"
        data = {
            "value": value,
            "dt": datetime.now(UTC).strftime("%d-%m-%Y %H:%M:%S"),
        }
        await redis_server.set(key, json.dumps(data))
        print(f" -> Redis SET {key} = {data}")

    async def _create_initial_extremums(self, pos_uuid: uuid.UUID, price: float):
        """
        Создаёт начальные экстремумы (MIN и MAX) в Redis.
        """
        await self._update_extremum(pos_uuid, "MIN", price)
        await self._update_extremum(pos_uuid, "MAX", price)