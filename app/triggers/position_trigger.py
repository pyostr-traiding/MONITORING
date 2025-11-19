import json
import logging

from app.services.position.router import PositionRouter
from app.triggers.base_trigger import BaseTrigger
from conf.conf_redis import redis_server_data

logger = logging.getLogger(__name__)


class PositionTrigger(BaseTrigger):
    channel_name = "kline:BTCUSDT"
    target_queue = "queue_monitoring_position"

    def __init__(self, handler):
        super().__init__(handler)
        self.service = PositionRouter()

    async def handle(self, trigger_data):
        if not self.handler.messages:
            logger.info("[Trigger:Position] Очередь пуста")
            return

        iterations = len(self.handler)
        logger.info(f"[Trigger:Position] Обрабатываю {iterations} сообщений")

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
                logger.error(f"[Trigger:Position] Ошибка обработчика: {e}")
                result = False

            if result:
                logger.info(f"[Trigger:Position] ✅ Удаляю {body.get('uuid')}")
                await self.handler.remove_message(item)
                await redis_server_data.publish(
                    'MONITORING',
                    json.dumps(
                        {
                            'id': body.get('id'),
                            'type': 'position',
                            'method': 'delete',
                        }
                    )
                )
                await redis_server_data.delete('position:' + str(body.get('id')))

            else:
                logger.info(f"[Trigger:Position] ⏳ Ещё не готово → в конец {body.get('uuid')}")
                await self.handler.requeue_message(item)
