# config.py
"""
Файл конфигурации для всего приложения.
Можно расширять — например, добавить логгинг, переменные окружения и т.д.
"""
import os

import aiohttp
import redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_URL = os.getenv('RABBITMQ_URL')

RABBITMQ_QUEUES = {
    "positions": "queue_monitoring_position",
    "orders": "queue_monitoring_order",
}

REDIS_CONFIG = {
    "host": os.getenv('REDIS_HOST'),
    "port": os.getenv('REDIS_PORT'),
    "db": 0,
    "password": os.getenv('REDIS_PASSWORD'),
}
REDIS_CHANNELS = ["kline:BTCUSDT"]

API_BASE_URL = "http://" + os.getenv('API_BASE_URL') + ':8000/api'
print(API_BASE_URL)
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=15)

BASE_HEADERS = {}

redis_server = aioredis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=int(os.getenv('REDIS_PORT')),
    password=os.getenv('REDIS_PASSWORD'),
    db=3,
    decode_responses=True
)