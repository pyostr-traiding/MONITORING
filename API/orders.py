import aiohttp
import asyncio

from config import API_BASE_URL, DEFAULT_TIMEOUT


async def api_get_list_orders() -> list[dict]:
    """Запрашивает список открытых ордеров с API"""
    url = f"{API_BASE_URL}/order/ListOpen"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=DEFAULT_TIMEOUT) as resp:
                if resp.status != 200:
                    print(f"[InitLoader] Ошибка {resp.status} при запросе {url}")
                    return []
                data = await resp.json()
                if not isinstance(data, list):
                    print(f"[InitLoader] Невалидный ответ (ожидался list) с {url}")
                    return []
                print(f"[InitLoader] Получено {len(data)} элементов с order/ListOpen")
                return data
    except Exception as e:
        print(f"[InitLoader] Ошибка при запросе {url}: {e}")
        return []

