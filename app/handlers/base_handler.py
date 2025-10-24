import asyncio
import json

class BaseHandler:
    def __init__(self):
        self.messages: list[dict] = []  # локальные сообщения
        self.lock = asyncio.Lock()
        self.queue_name = None

    def __len__(self):
        return len(self.messages)

    async def add_message(self, msg, body):
        """Добавляем сообщение в локальную очередь (RabbitMQ msg, JSON body)"""
        async with self.lock:
            # Преобразуем строку JSON → dict (если нужно)
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except json.JSONDecodeError:
                    pass

            uuid = (body or {}).get("uuid")
            if uuid:
                # 🔸 Проверяем, нет ли уже такого uuid в очереди
                if any(m["body"].get("uuid") == uuid for m in self.messages):
                    print(f"[Handler:{self.__class__.__name__}] 🔁 Пропускаю дубликат uuid={uuid}")
                    if msg:
                        await msg.ack()  # подтверждаем получение, чтобы не висело в Rabbit
                    return

            # 🔸 Добавляем в локальную очередь
            self.messages.append({"msg": msg, "body": body})
            print(f"[Handler:{self.__class__.__name__}] Добавлено сообщение: {body}")

            # 🔹 Подтверждаем RabbitMQ, если есть msg
            if msg:
                await msg.ack()

    async def get_messages(self):
        """Возвращает копию текущих сообщений"""
        async with self.lock:
            return list(self.messages)

    async def next_message(self):
        """Берём следующее сообщение (FIFO)"""
        async with self.lock:
            if not self.messages:
                return None
            return self.messages.pop(0)

    async def requeue_message(self, item):
        """Возвращаем сообщение в конец очереди"""
        async with self.lock:
            self.messages.append(item)

    async def remove_message(self, item):
        """Удаляем сообщение"""
        async with self.lock:
            try:
                self.messages.remove(item)
            except ValueError:
                pass
