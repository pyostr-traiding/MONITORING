import asyncio
from typing import Callable, Dict, List, Optional

import aio_pika


class RabbitMQConsumer:
    """
    - reconnect с backoff
    - prefetch (QoS), чтобы не заливать воркеров
    - ack сразу после помещения в локальную очередь (транспорт ≠ storage)
    - аккуратное закрытие
    """
    def __init__(self, url: str, prefetch: int = 64, reconnect_attempts: int = 5, reconnect_base_delay: float = 1.0):
        self.url = url
        self.prefetch = prefetch
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_base_delay = reconnect_base_delay

        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.callbacks: Dict[str, Callable] = {}
        self._consuming_queues: List[str] = []
        self._closing = asyncio.Event()

    def register_callback(self, queue_name: str, callback: Callable):
        """Привязывает локальный callback (handler.add_message) к очереди"""
        self.callbacks[queue_name] = callback

    async def connect(self):
        """Подключение с экспоненциальным backoff."""
        last_exc = None
        for attempt in range(1, self.reconnect_attempts + 1):
            try:
                self.connection = await aio_pika.connect_robust(self.url)
                self.channel = await self.connection.channel()
                await self.channel.set_qos(prefetch_count=self.prefetch)
                print(f"[RabbitMQ] Connected (attempt {attempt})")
                return
            except Exception as e:
                last_exc = e
                delay = self.reconnect_base_delay * attempt
                print(f"[RabbitMQ] connect failed ({attempt}/{self.reconnect_attempts}): {e} → retry in {delay:.1f}s")
                await asyncio.sleep(delay)
        raise RuntimeError(f"RabbitMQ connect failed after {self.reconnect_attempts} attempts: {last_exc}")

    async def start(self, queue_names: List[str]):
        """Запуск подписок на очереди."""
        assert self.channel is not None, "call connect() first"
        self._consuming_queues = list(queue_names)
        for q_name in queue_names:
            queue = await self.channel.declare_queue(q_name, durable=True)

            async def on_message(message: aio_pika.IncomingMessage, q=q_name):
                """
                Читаем, кладём локально, затем ACK.
                Не используем auto-ack контекст, чтобы самим контролировать подтверждение.
                """
                try:
                    body = message.body.decode()
                    cb = self.callbacks.get(q)
                    if cb:
                        # кладём локально (msg=None, т.к. мы подтверждаем сразу)
                        await cb(None, body)
                        print(f"[RabbitMQ] {q} → {body}")
                    # подтверждаем немедленно: транспорт освобождаем сразу
                    await message.ack()
                except Exception as e:
                    # безопаснее nack с requeue, чтобы не потерять при сбое callback
                    print(f"[RabbitMQ] on_message error, nack requeue: {e}")
                    try:
                        await message.nack(requeue=True)
                    except Exception as _:
                        pass  # уже не страшно

            await queue.consume(on_message, no_ack=False)
            print(f"[RabbitMQ] Listening: {q_name}")

    async def close(self):
        """Аккуратно закрыть соединения."""
        self._closing.set()
        try:
            if self.channel:
                await self.channel.close()
        finally:
            if self.connection:
                await self.connection.close()
        print("[RabbitMQ] Closed")
