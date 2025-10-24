class BaseTrigger:
    """Базовый триггер для Redis PubSub"""
    channel_name = None  # имя канала Redis

    def __init__(self, handler):
        self.handler = handler

    async def handle(self, trigger_data):
        # raise NotImplementedError
        pass