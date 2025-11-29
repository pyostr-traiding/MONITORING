# config.py
"""
Файл конфигурации для всего приложения.
Можно расширять — например, добавить логгинг, переменные окружения и т.д.
"""
import os

import aiohttp

from dotenv import load_dotenv

from infisical_sdk import InfisicalSDKClient


load_dotenv()



# Инициализация клиента
client = InfisicalSDKClient(
    host=os.getenv('INFISICAL_HOST'),
    token=os.getenv('INFISICAL_TOKEN'),
    cache_ttl=300
)


def load_project_secrets(project_slug: str):
    resp = client.secrets.list_secrets(
        project_slug=project_slug,
        environment_slug=os.getenv('ENVIRONMENT_SLUG'),
        secret_path="/"
    )
    return {s['secretKey']: s['secretValue'] for s in resp.to_dict()['secrets']}

# Загружаем общие секреты
shared_secrets = load_project_secrets("shared-all")

# Загружаем проектные секреты
project_secrets = load_project_secrets("monitoring")

# Объединяем: проектные перезаписывают общие при совпадении ключей
all_secrets = {**shared_secrets, **project_secrets}

# Добавляем в окружение
os.environ.update(all_secrets)


class Settings:

    SYMBOL: str = os.getenv('SYMBOL')

    API_BASE_URL: str = os.getenv('BASE_API_URL')


    REDIS_HOST: str = os.getenv('REDIS_HOST')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT'))
    REDIS_PASSWORD: str = os.getenv('REDIS_PASSWORD')

    RABBITMQ_URL: str = os.getenv('RABBITMQ_URL')

    INFISICAL_HOST: str = os.getenv('INFISICAL_HOST')
    INFISICAL_TOKEN: str = os.getenv('INFISICAL_TOKEN')
    REDIS_CONFIG = {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "db": 0,
        "password": REDIS_PASSWORD,
    }
    REDIS_CHANNELS = ["kline:BTCUSDT"]

settings = Settings()

#
# if 'https:' in os.getenv('API_BASE_URL'):
#     API_BASE_URL = os.getenv('API_BASE_URL')
# else:
#     API_BASE_URL = "http://" + os.getenv('API_BASE_URL') + ':8000/api'

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=15)

BASE_HEADERS = {}

