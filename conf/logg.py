import logging
import logging.config
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}:{lineno} — {message}',
            'style': '{',
            'datefmt': '%d-%m-%Y %H:%M:%S',
        },
        'colored': {
            '()': 'colorlog.ColoredFormatter',
            'format': '%(log_color)s[%(asctime)s] %(levelname)s %(name)s: %(message)s',
        },
    },

    'handlers': {
        'console_debug': {
            'class': 'logging.StreamHandler',
            'formatter': 'colored',
            'level': 'DEBUG',
        },
        'console_production': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'level': 'ERROR',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': str('logs/app.log'),
            'formatter': 'verbose',
            'level': 'INFO',
        },
        'rotating': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str('logs/app_rotating.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 3,
            'formatter': 'verbose',
            'level': 'INFO',
        },
    },

    'loggers': {
        # Корневой логгер для всех модулей
        '': {
            'handlers': ['console_debug', 'rotating'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Отдельный логгер для конкретного пакета
        'app': {
            'handlers': ['console_debug', 'rotating'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}


def setup_logging():
    """Инициализация логгера"""
    import os
    os.makedirs('logs', exist_ok=True)
    logging.config.dictConfig(LOGGING)
