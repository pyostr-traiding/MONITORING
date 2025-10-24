# main.py
import sys
import asyncio
from config import RABBITMQ_URL, REDIS_CONFIG, REDIS_CHANNELS, API_BASE_URL
from app.core.rabbitmq_consumer import RabbitMQConsumer
from app.core.redis_listener import RedisListener
from app.core.registry import load_handlers, load_triggers
from app.core.initializer import InitialDataLoader



# 🧹 очищаем кэш, чтобы гарантированно не схватить старые классы
for mod in list(sys.modules.keys()):
    if mod.startswith("app.handlers") or mod.startswith("app.triggers"):
        del sys.modules[mod]


def print_bind_table(bindings: list[tuple]):
    """Выводит таблицу связей триггеров и хендлеров"""
    if not bindings:
        print("[Bind] Нет активных связей.")
        return

    print("\n┌────────────────────────┬──────────────────────────┬──────────────────────────┐")
    print("│ {:<22} │ {:<24} │ {:<24} │".format("Trigger", "Redis Channel", "Handler Queue"))
    print("├────────────────────────┼──────────────────────────┼──────────────────────────┤")

    for trigger, channel, queue in bindings:
        print("│ {:<22} │ {:<24} │ {:<24} │".format(trigger, channel, queue))

    print("└────────────────────────┴──────────────────────────┴──────────────────────────┘\n")


async def main():
    # === 1. Загружаем классы ===
    handler_classes = load_handlers()
    trigger_classes = load_triggers()

    handlers = [cls() for cls in handler_classes]
    print(f"[Init] Найдено обработчиков: {len(handlers)}")

    # === 2. Первичная загрузка ===
    loader = InitialDataLoader(API_BASE_URL, handlers)
    await loader.load_all()
    print("[Init] Первичная загрузка данных завершена")

    # === 3. Инициализация RabbitMQ ===
    rabbit = RabbitMQConsumer(RABBITMQ_URL)
    await rabbit.connect()

    for handler in handlers:
        if handler.queue_name:
            rabbit.register_callback(handler.queue_name, handler.add_message)

    await rabbit.start([h.queue_name for h in handlers if h.queue_name])

    # === 4. Redis Listener ===
    redis_listener = RedisListener(REDIS_CONFIG, REDIS_CHANNELS, handlers)
    bindings = []
    active_triggers = []  # 🧩 сюда положим все триггеры (даже временные)

    print("\n[DEBUG] Handlers list:")
    for h in handlers:
        print(f"  {h.__class__.__name__}: queue_name={h.queue_name}")

    print("\n[DEBUG] Triggers list:")
    for t in trigger_classes:
        print(f"  {t.__name__}: target_queue={getattr(t, 'target_queue', None)}, channel_name={getattr(t, 'channel_name', None)}")

    for trigger_class in trigger_classes:
        target_queue = getattr(trigger_class, "target_queue", None)
        if not target_queue:
            print(f"[WARN] У {trigger_class.__name__} не задан target_queue — пропуск")
            continue

        handler = next((h for h in handlers if str(h.queue_name) == str(target_queue)), None)

        if not handler:
            from app.handlers.base_handler import BaseHandler
            handler = BaseHandler()
            handler.queue_name = target_queue
            print(f"[INFO] 🧩 Создан временный хендлер для {trigger_class.__name__} (очередь {target_queue})")

        trigger = trigger_class(handler)
        active_triggers.append(trigger)

        if getattr(trigger, "channel_name", None):
            redis_listener.register_callback(trigger.channel_name, trigger.handle)
            bindings.append((trigger_class.__name__, trigger.channel_name, handler.queue_name))
            print(f"[Bind] ✅ {trigger_class.__name__} ↔ {handler.__class__.__name__}")

    print(f"[Init] Найдено триггеров: {len(trigger_classes)}")
    print_bind_table(bindings)

    # === 🔧 Подмена временных хендлеров на реальные ===
    real_handlers = {h.queue_name: h for h in handlers}
    for trigger in active_triggers:
        q = getattr(trigger.handler, "queue_name", None)
        if q in real_handlers and not isinstance(trigger.handler, real_handlers[q].__class__):
            trigger.handler = real_handlers[q]
            print(f"[Fix] 🔁 Обновил handler у {trigger.__class__.__name__} → {trigger.handler.__class__.__name__}")

    # === 5. Redis слушатель ===
    redis_task = asyncio.create_task(redis_listener.start())

    try:
        await redis_task
    except asyncio.CancelledError:
        print("[Main] Завершение по Ctrl+C")
    finally:
        print("[Main] Закрываю соединения...")
        await rabbit.connection.close()
        await redis_listener.pubsub.aclose()
        await redis_listener.redis.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Завершение работы...")
