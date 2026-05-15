"""Загрузка конфигурации из .env."""

from pathlib import Path

from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv(BASE_DIR / ".env.example")


def get_db_path() -> Path:
    raw = os.getenv("DB_PATH", "data/cookbook.sqlite")
    path = Path(raw)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


def get_default_unit() -> str:
    return os.getenv("DEFAULT_UNIT", "шт.")


def get_log_level() -> str:
    return os.getenv("LOG_LEVEL", "INFO")
