# ==============================================================
# ФЬЮЧЕРСЫ / ОПЦИОНЫ
# ==============================================================
import datetime
import logging
from typing import Union

from API.position import api_get_position, api_change_status_position
from API.schemas.position import PositionSchema

from app.schemas.kline import KlineUpdate
from app.services.position.services.position_service import BasePositionService
from conf.conf_redis import redis_server_settings

from cachetools import TTLCache, cached


logger = logging.getLogger(__name__)

cache_life_time_value = TTLCache(maxsize=100, ttl=5)

@cached(cache=cache_life_time_value)
def get_cached_life_time_value() -> int:
    time = redis_server_settings.get('settings:position-lifetime-seconds')
    if not time:
        return 5
    else:
        return int(time)

async def dt_lifetime_position_expire(position: PositionSchema) -> bool:
    # created_at приходит в формате ISO: "2025-11-21T05:19:13.852Z"
    created_str: str = position.created_at
    # Парсим дату
    created_dt = datetime.datetime.fromisoformat(created_str.replace("Z", "+00:00"))
    # Берём TTL в секундах (например, 60)
    ttl_seconds = get_cached_life_time_value()
    # Время истечения
    expires_at = created_dt + datetime.timedelta(seconds=ttl_seconds)
    # Текущее время
    now = datetime.datetime.now(datetime.UTC)
    # Если текущее время >= истечения — просрочено
    if now >= expires_at:
        return True
    return False

class OptionPositionService(BasePositionService):
    async def _handle_option(self, position: PositionSchema, kline: KlineUpdate) -> bool:
        current_price = float(kline.data.data.c)
        if await dt_lifetime_position_expire(position):
            result_accept = await api_change_status_position(
                uuid=position.uuid,
                status='cancel'
            )
            print(result_accept)
            if not result_accept:
                return False
            return True
        if not await self.has_position(position.id):
            api_position = await api_get_position(uuid=position.uuid)
            if api_position is None:
                return False
            if api_position is False:
                logger.info(f'Отмена статусом: {position}')
                return True
            result_accept = await api_change_status_position(
                uuid=position.uuid,
                status='monitoring'
            )
            if not result_accept:
                return False
            await self._add_new_option_position(position, kline)
            return False

        await self._update_option_extremums(position.id, current_price)
        result = await self.calculation(position, kline)
        return result

    async def _add_new_option_position(self, position: PositionSchema, kline: KlineUpdate):
        pos_uuid = position.uuid
        min_val, max_val = await self._load_existing_extremums(pos_uuid)

        kline_data = kline.data.data
        market_min = float(kline_data.l)
        market_max = float(kline_data.h)
        market_close = float(kline_data.c)

        if min_val is None or max_val is None:
            min_val = market_min
            max_val = market_max
            await self._create_initial_extremums(pos_uuid, market_close)
            logger.info(
                f"[INIT] Экстремумы не найдены — установлены по рынку: "
                f"MIN={market_min}, MAX={market_max}"
            )
        else:
            logger.info(f"[LOAD] Найдены экстремумы в Redis: MIN={min_val} MAX={max_val}")

        await self.set_position(position.id, {  # <--- await
            "uuid": pos_uuid,
            "symbol": position.symbol_name,
            "side": position.side,
            "price_entry": float(position.price),
            "max_price": float(max_val),
            "min_price": float(min_val),
        })

        logger.info(f"[NEW] {position.symbol_name} ({position.side}) по {position.price}")

    async def _update_option_extremums(self, position_id: int, current_price: float):
        pos = await self.get_position(position_id)  # <--- await
        if not pos:
            logger.error(f"Позиция {position_id} не найдена в redis для обновления экстремумов.")
            return
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
            await self.set_position(position_id, pos)  # <--- await
            logger.info(
                f"[UPDATE] {pos['symbol']} ({pos['side']}) | "
                f"MIN={pos['min_price']:.2f} | MAX={pos['max_price']:.2f}"
            )

    async def calculation(
            self,
            position: PositionSchema,
            kline: KlineUpdate
    ) -> bool:
        """
        Проверяет, достигла ли цена уровня входа.
        Если достигла — обновляем статус позиции на 'completed'.
        Панель сама откроет ордер после подтверждения на бирже.
        """

        # Извлекаем нужные данные
        try:
            price = float(position.price)
            low = float(kline.data.data.l)
            high = float(kline.data.data.h)
            ts = str(kline.data.data.ts)
        except (AttributeError, ValueError, TypeError) as e:
            logger.error(f'Ошибка в данных для расчёта: {e}, position={position}, kline={kline}')
            return False

        # Если уже закрыта или завершена — не трогаем
        if position.status in ('completed', 'canceled'):
            logger.debug(f'Пропуск: позиция уже завершена {position.uuid}')
            return False

        # Проверяем условия входа
        entered = False
        side = position.side.lower()

        # Для покупки: цена входа попадает в диапазон свечи
        if side == 'buy' and low <= price <= high:
            entered = True

        # Для продажи: то же, диапазон свечи "задел" цену входа
        elif side == 'sell' and low <= price <= high:
            entered = True

        # Если условие сработало — обновляем статус
        if entered:
            logger.info(f'Сделка открыта: {position.symbol_name} ({position.side.upper()}) '
                        f'по цене {price}, UUID={position.uuid}')
            try:
                result = await api_change_status_position(
                    uuid=position.uuid,
                    status='completed',
                    kline_ms=ts
                )
                return bool(result)
            except Exception as e:
                logger.error(f'Ошибка при обновлении статуса позиции {position.uuid}: {e}')
                return False

        # Не достигли цены — продолжаем мониторинг
        return False
