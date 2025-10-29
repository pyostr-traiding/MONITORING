import logging

import aiohttp

from typing import Union, Literal

from API.schemas.position import PositionSchema
from conf.config import DEFAULT_TIMEOUT, API_BASE_URL, BASE_HEADERS

logger = logging.getLogger(__name__)


async def api_get_position(
        uuid: str
) -> Union[PositionSchema, bool, None]:
    """
    Получить позицию
    """
    params = {
        'uuid': uuid,
    }
    url = f"{API_BASE_URL}/position/"
    async with aiohttp.ClientSession() as session:
        async with session.get(
                url=url,
                params=params,
                headers=BASE_HEADERS,
                timeout=DEFAULT_TIMEOUT,
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                position_schema = PositionSchema.model_validate(data)
                if position_schema.status in ['completed', 'cancel']:
                    return False
                return position_schema
            return None


async def api_get_list_positions() -> list[dict]:
    """
    Запрашивает список открытых ордеров с API
    """
    url = f"{API_BASE_URL}/position/ListOpen"
    print(url)
    async with aiohttp.ClientSession() as session:
        async with session.get(
                url,
                headers=BASE_HEADERS,
                timeout=DEFAULT_TIMEOUT,
        ) as resp:
            if resp.status != 200:
                logger.error(f"[InitLoader] Ошибка {resp.status} при запросе {url}")
                return []
            data = await resp.json()
            if not isinstance(data, list):
                logger.error(f"[InitLoader] Невалидный ответ (ожидался list) с {url}")
                return []
            logger.info(f"[InitLoader] Получено {len(data)} элементов с position/ListOpen")
            return data


async def api_change_status_position(
        uuid: str,
        status: Literal['monitoring', 'completed', 'cancel'],
        kline_ms: str = None
) -> Union[bool, None]:
    """
    Изменение статуса
    False - Действие невозможно
    True - Действие выполнено
    None - Ошибка выполнения, попробуйте еще раз
    """
    data = {
        'uuid': uuid,
        'status': status,
        'kline_ms': kline_ms,
    }
    url = f"{API_BASE_URL}/position/changeStatus"
    async with aiohttp.ClientSession() as session:
        async with session.post(
                url,
                json=data,
                headers=BASE_HEADERS,
                timeout=DEFAULT_TIMEOUT,
        ) as resp:
            if resp.status == 200:
                return True
            if resp.status == 409:
                return True
            if resp.status == 404:
                return False
            if resp.status == 500:
                return None
            return None
