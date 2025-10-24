import json

from app.services.position.router import PositionRouter
from app.triggers.base_trigger import BaseTrigger
from app.services.position.services.position_service import BasePositionService


class PositionTrigger(BaseTrigger):
    channel_name = "kline:BTCUSDT"
    target_queue = "queue_monitoring_position"

    def __init__(self, handler):
        super().__init__(handler)
        self.service = PositionRouter()

    async def handle(self, trigger_data):
        if not self.handler.messages:
            print("[Trigger:Position] Очередь пуста")
            return

        iterations = len(self.handler)
        print(f"[Trigger:Position] Обрабатываю {iterations} сообщений")

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
                print(f"[Trigger:Position] Ошибка обработчика: {e}")
                result = False

            if result:
                print(f"[Trigger:Position] ✅ Удаляю {body.get('uuid')}")
                await self.handler.remove_message(item)
            else:
                print(f"[Trigger:Position] ⏳ Ещё не готово → в конец {body.get('uuid')}")
                await self.handler.requeue_message(item)
