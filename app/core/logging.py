import logging
import sys
from typing import Dict, Any
from pythonjsonlogger import json

from .config import settings


def setup_logging() -> None:
    """Настройка логирования"""

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    if settings.LOG_FORMAT == "json":
        formatter = json.JsonFormatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s',
            json_ensure_ascii=False
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if settings.LOG_FILE:
        try:
            file_handler = logging.FileHandler(settings.LOG_FILE)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except (PermissionError, FileNotFoundError) as e:
            logger.warning(f"Cannot create log file: {e}")

    logging.getLogger("uvicorn").handlers.clear()
    logging.getLogger("uvicorn").addHandler(console_handler)

    if settings.LOG_FILE:
        try:
            uvicorn_file_handler = logging.FileHandler(settings.LOG_FILE)
            uvicorn_file_handler.setFormatter(formatter)
            logging.getLogger("uvicorn").addHandler(uvicorn_file_handler)
        except (PermissionError, FileNotFoundError):
            pass


def get_logger(name: str) -> logging.Logger:
    """Получить логгер с указанным именем"""

    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """Адаптер для логгера с дополнительными полями"""

    def __init__(self, logger: logging.Logger, extra: Dict[str, Any] = None):
        super().__init__(logger, extra or {})

    def process(self, msg, kwargs):
        """Добавляем дополнительные поля в логи"""

        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra'].update(self.extra)
        return msg, kwargs
