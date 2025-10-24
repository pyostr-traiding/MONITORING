from app.handlers.base_handler import BaseHandler

class OrderHandler(BaseHandler):
    """Обработчик сообщений очереди ордеров"""
    def __init__(self):
        super().__init__()
        self.queue_name = "queue_monitoring_order"
