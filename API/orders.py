import asyncio
import logging
from decimal import Decimal
from typing import Literal, Union

import aiohttp
from dotenv import load_dotenv

from API.schemas.order import OrderSchema
from conf.config import API_BASE_URL, DEFAULT_TIMEOUT, BASE_HEADERS

logger = logging.getLogger(__name__)

load_dotenv()
async def api_get_order(
        uuid: str
) -> Union[OrderSchema, bool, None]:
    """
    Получить ордер
    """
    params = {
        'uuid': uuid,
    }
    url = f"{API_BASE_URL}/order/"
    async with aiohttp.ClientSession() as session:
        async with session.get(
                url=url,
                params=params,
                headers=BASE_HEADERS,
                timeout=DEFAULT_TIMEOUT,
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                position_schema = OrderSchema.model_validate(data)
                if position_schema.status in ['completed', 'cancel']:
                    return False
                return position_schema
            return None


async def api_get_list_orders() -> list[dict]:
    """Запрашивает список открытых ордеров с API"""
    url = f"{API_BASE_URL}/order/ListOpen"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    url=url,
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
                logger.info(f"[InitLoader] Получено {len(data)} элементов с order/ListOpen")
                return data
    except Exception as e:
        logger.error(f"[InitLoader] Ошибка при запросе {url}: {e}")
        return []


async def api_change_status_order(
        uuid: str,
        status: Literal['monitoring', 'completed', 'cancel'],

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
    }
    url = f"{API_BASE_URL}/order/changeStatus"
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


async def api_close_order(
        uuid: str,
        rate: Decimal,
        kline_ms: int

) -> Union[bool, None]:
    """
    Изменение статуса
    False - Действие невозможно
    True - Действие выполнено
    None - Ошибка выполнения, попробуйте еще раз
    """
    data = {
        'uuid': uuid,
        'rate': str(rate),
        'kline_ms': kline_ms,
    }
    url = f"{API_BASE_URL}/order/close"
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
            if resp.status == 424:
                return True
            if resp.status == 404:
                return False
            if resp.status == 500:
                return None
            return None
