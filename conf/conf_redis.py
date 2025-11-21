import os

from dotenv import load_dotenv
from redis import asyncio as aioredis
import redis
load_dotenv()

redis_server_data = aioredis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=int(os.getenv('REDIS_PORT')),
    password=os.getenv('REDIS_PASSWORD'),
    db=8,
)

redis_server_settings = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=int(os.getenv('REDIS_PORT')),
    password=os.getenv('REDIS_PASSWORD'),
    db=1,
)