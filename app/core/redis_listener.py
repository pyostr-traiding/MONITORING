# app/core/redis_listener.py
import json
import asyncio
import time
from typing import Callable, Dict, List
import redis.asyncio as aioredis


class RedisListener:
    def __init__(self, config: dict, channels: List[str], handlers: List, reconnect_delay: float = 2.0):
        self.config = config
        self.channels = channels
        self.handlers = handlers  # 🔹 добавили список всех хендлеров
        self.callbacks: Dict[str, List[Callable]] = {}
        self.redis: aioredis.Redis | None = None
        self.pubsub: aioredis.client.PubSub | None = None
        self.reconnect_delay = reconnect_delay
        self._stop = asyncio.Event()
        self._last_call: Dict[str, float] = {}  # debounce

    def register_callback(self, channel: str, callback: Callable):
        if channel not in self.callbacks:
            self.callbacks[channel] = []
        self.callbacks[channel].append(callback)

    async def _queues_empty(self) -> bool:
        """Проверяем, все ли очереди пустые"""
        for h in self.handlers:
            if h.messages:  # локальная очередь не пуста
                return False
        return True

    async def start(self):
        while not self._stop.is_set():
            try:
                self.redis = aioredis.Redis(**self.config, decode_responses=True)
                self.pubsub = self.redis.pubsub()
                await self.pubsub.subscribe(*self.channels)
                print(f"[Redis] Подписан на каналы: {self.channels}")

                async for raw in self.pubsub.listen():
                    if self._stop.is_set():
                        break
                    if raw["type"] != "message":
                        continue

                    # 💡 Если все очереди пусты — пропускаем событие
                    if await self._queues_empty():
                        # (Опционально можно логировать раз в N минут)
                        continue

                    channel = raw["channel"]
                    try:
                        data = json.loads(raw["data"])
                    except Exception:
                        data = raw["data"]

                    # 🔹 1. фильтруем по типу свечи
                    interval = data.get("interval") if isinstance(data, dict) else None
                    if interval and interval != "1m":
                        continue  # игнорируем 5m, 15m, 30m

                    # 🔹 2. debounce: не чаще 1 раза в 3 секунды
                    now = time.monotonic()
                    last = self._last_call.get(channel, 0)
                    if now - last < 3:
                        continue
                    self._last_call[channel] = now

                    # 🔹 3. запуск callback'ов (в фоне)
                    for cb in self.callbacks.get(channel, []):
                        asyncio.create_task(cb(data))
            except Exception as e:
                print(f"[Redis] listen error: {e} → reconnect in {self.reconnect_delay}s")
                await asyncio.sleep(self.reconnect_delay)
            finally:
                try:
                    if self.pubsub:
                        await self.pubsub.aclose()
                except Exception:
                    pass
                try:
                    if self.redis:
                        await self.redis.aclose()
                except Exception:
                    pass

    async def stop(self):
        self._stop.set()
