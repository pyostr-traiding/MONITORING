import os

from dotenv import load_dotenv
from redis import asyncio as aioredis
import redis

from conf.config import settings

load_dotenv()

redis_server_data = aioredis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=8,
)

redis_server_settings = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=1,
)
redis_server = aioredis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=3,
    decode_responses=True
)

