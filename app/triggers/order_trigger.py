import json
import logging

from app.services.order.router import OrderRouter
from app.triggers.base_trigger import BaseTrigger

logger = logging.getLogger(__name__)


class OrderTrigger(BaseTrigger):
    channel_name = "kline:BTCUSDT"
    target_queue = "queue_monitoring_order"  # ← вот это важно!

    def __init__(self, handler):
        super().__init__(handler)
        self.service = OrderRouter()

    async def handle(self, trigger_data):
        if not self.handler.messages:
            logger.info("[Trigger:Order] Очередь пуста")
            return

        iterations = len(self.handler)
        logger.info(f"[Trigger:Order] Обрабатываю {iterations} сообщений")

        for _ in range(iterations):
            item = await self.handler.next_message()
            if not item:
                break
            msg = item["msg"]
            body = item["body"]
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except Exception:
                    pass

            try:
                result = await self.service.process(body, trigger_data)
            except Exception as e:
                logger.error(f"[Trigger:Order] Ошибка обработчика: {e}")
                result = False

            if result:
                logger.info(f"[Trigger:Order] ✅ Удаляю {body.get('uuid')}")
                await self.handler.remove_message(item)
            else:
                logger.info(f"[Trigger:Order] ⏳ Ещё не готово → в конец {body.get('uuid')}")
                await self.handler.requeue_message(item)
