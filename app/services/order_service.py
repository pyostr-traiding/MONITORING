import asyncio
import random


class OrderService:
    async def process(self, order: dict, trigger_data: dict) -> bool:
        """
        True  -> удаляем из локальной очереди
        False -> крутим дальше (requeue)
        """
        await asyncio.sleep(0.05)  # имитация IO
        is_ready = random.random() < 0.4
        if is_ready:
            print("[OrderService] ✅ Ордер готов")
        else:
            print("[OrderService] ⏳ Ордер ещё не готов")
        return is_ready
