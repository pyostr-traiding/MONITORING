from app.handlers.base_handler import BaseHandler

class PositionHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.queue_name = "queue_monitoring_position"
