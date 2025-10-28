import logging

import aiohttp
import asyncio

from API.orders import api_get_list_orders
from API.position import api_get_list_positions

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=15)

logger = logging.getLogger(__name__)


async def process_positions_data(data_list: list[dict]) -> list[dict]:
    """Фильтрация и предобработка позиций"""
    processed = []
    for item in data_list:
        if item.get("status") in ["cancel", "completed"]:
            continue
        processed.append(item)
    logger.info(f"[InitLoader] Отфильтровано позиций: {len(processed)} из {len(data_list)}")
    return processed


async def process_orders_data(data_list: list[dict]) -> list[dict]:
    """Фильтрация и предобработка ордеров"""
    processed = []
    for item in data_list:
        if item.get("status") in ["cancel", "completed"]:
            continue
        item["full_symbol"] = f"{item.get('symbol', '').upper()}_{item.get('side', '').upper()}"
        processed.append(item)
    logger.info(f"[InitLoader] Отфильтровано ордеров: {len(processed)} из {len(data_list)}")
    return processed


# === 🧩 КЛАСС ЗАГРУЗЧИКА ===

class InitialDataLoader:
    """
    Первичная загрузка данных с API в handlers.
    Таймауты + мягкие ошибки.
    """
    def __init__(self, base_url: str, handlers: list):
        self.base_url = base_url.rstrip("/")
        self.handlers = handlers

    async def _process_data(self, handler, data_list: list[dict]):
        """Передаёт данные в хендлер"""
        for item in data_list:
            await handler.add_message(None, item)

    async def load_all(self):
        """Загружает данные по всем хендлерам"""
        tasks = []
        for handler in self.handlers:
            if handler.queue_name == "queue_monitoring_position":
                tasks.append(self._load_positions(handler))
            elif handler.queue_name == "queue_monitoring_order":
                tasks.append(self._load_orders(handler))
        await asyncio.gather(*tasks)

    async def _load_positions(self, handler):
        data = await api_get_list_positions()
        if not data:
            return
        processed = await process_positions_data(data)
        await self._process_data(handler, processed)

    async def _load_orders(self, handler):
        data = await api_get_list_orders()
        if not data:
            return
        processed = await process_orders_data(data)
        await self._process_data(handler, processed)