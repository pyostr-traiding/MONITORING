# ==============================================================
# ФЬЮЧЕРСЫ / ОПЦИОНЫ
# ==============================================================
import logging
from typing import Union

from API.position import api_get_position, api_change_status_position
from API.schemas.position import PositionSchema

from app.schemas.kline import KlineUpdate
from app.services.position.services.position_service import BasePositionService

logger = logging.getLogger(__name__)


class OptionPositionService(BasePositionService):
    async def _handle_option(self, position: PositionSchema, kline: KlineUpdate) -> bool:
        """
        Обработка фьючерсной позиции (option).
        """
        current_price = float(kline.data.data.c)
        # --- Если позиции ещё нет в локальном хранилище ---
        if position.id not in self._positions:
            api_position = await api_get_position(uuid=position.uuid)

            # Если не получили позицию с базы
            if api_position is None:
                return False

            # Если позиция в нерабочих статусах (пр. Исполнено)
            if api_position is False:
                logger.info(f'Отмена статусом: {position}')
                return True
                # Принимаем ордер
            result_accept = await api_change_status_position(
                uuid=position.uuid,
                status='monitoring'
            )
            if not result_accept:
                return False
            await self._add_new_option_position(position, kline)
            return False

        # --- Обновляем экстремумы ---
        await self._update_option_extremums(position.id, current_price)
        result = await self.calculation(position, kline)
        return result

    async def calculation(
            self,
            position: PositionSchema,
            kline: KlineUpdate
    ) -> Union[bool, None]:
        """
        Считаем имеется ли прибыль
        Если достигла точки входа - подтвердим позицию в базе и удалим локально
        """
        if position.side == 'buy':
            if float(position.price) <= kline.data.data.h:
                logger.info(f'Сделка открыта: {position}')
                result = await api_change_status_position(
                    uuid=position.uuid,
                    status='completed',
                    kline_ms=str(kline.data.data.ts)
                )
                return result
            return False
        if position.side == 'sell':
            if float(position.price) >= kline.data.data.h:
                logger.info(f'Сделка открыта: {position}')
                result = await api_change_status_position(
                    uuid=position.uuid,
                    status='completed',
                    kline_ms=str(kline.data.data.ts)
                )
                return result
            return False
        return False

    async def _add_new_option_position(self, position: PositionSchema, kline: KlineUpdate):
        """
        Добавляет новую фьючерсную позицию и подгружает экстремумы из Redis.
        Если экстремумов нет — берём их с рынка, а не из цены позиции.
        """
        pos_uuid = position.uuid
        min_val, max_val = await self._load_existing_extremums(pos_uuid)

        kline_data = kline.data.data
        market_min = float(kline_data.l)
        market_max = float(kline_data.h)
        market_close = float(kline_data.c)

        if min_val is None or max_val is None:
            # Используем рыночные экстремумы
            min_val = market_min
            max_val = market_max
            await self._create_initial_extremums(pos_uuid, market_close)
            logger.info(
                f"[INIT] Экстремумы не найдены — установлены по рынку: "
                f"MIN={market_min}, MAX={market_max}"
            )
        else:
            logger.info(f"[LOAD] Найдены экстремумы в Redis: MIN={min_val} MAX={max_val}")

        self._positions[position.id] = {
            "uuid": pos_uuid,
            "symbol": position.symbol_name,
            "side": position.side,
            "price_entry": float(position.price),
            "max_price": float(max_val),
            "min_price": float(min_val),
        }

        logger.info(f"[NEW] {position.symbol_name} ({position.side}) по {position.price}")

    async def _update_option_extremums(self, position_id: int, current_price: float):
        """
        Обновляет экстремумы для фьючерсной позиции.
        """
        pos = self._positions[position_id]
        pos_uuid = pos["uuid"]
        updated = False

        if current_price > pos["max_price"]:
            pos["max_price"] = current_price
            await self._update_extremum(pos_uuid, "MAX", current_price)
            updated = True

        if current_price < pos["min_price"]:
            pos["min_price"] = current_price
            await self._update_extremum(pos_uuid, "MIN", current_price)
            updated = True

        if updated:
            logger.info(
                f"[UPDATE] {pos['symbol']} ({pos['side']}) | "
                f"MIN={pos['min_price']:.2f} | MAX={pos['max_price']:.2f}"
            )
