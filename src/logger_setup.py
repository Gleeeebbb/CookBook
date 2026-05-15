"""Настройка логирования в app.log."""

import logging
from pathlib import Path

from config import BASE_DIR, get_log_level

LOG_FILE = BASE_DIR / "app.log"


def setup_logging() -> logging.Logger:
    level_name = get_log_level().upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger("cookbook")
    logger.setLevel(level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)
    logger.addHandler(console_handler)

    return logger
