"""Работа с SQLite: схема и подключение."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from config import get_db_path


def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                cook_time_min INTEGER NOT NULL,
                ingredients_json TEXT NOT NULL,
                instructions TEXT NOT NULL,
                calories_per_serving REAL,
                added_date TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS meal_plans (
                date TEXT PRIMARY KEY,
                breakfast_id INTEGER,
                lunch_id INTEGER,
                dinner_id INTEGER,
                snacks_ids_json TEXT,
                FOREIGN KEY (breakfast_id) REFERENCES recipes(id),
                FOREIGN KEY (lunch_id) REFERENCES recipes(id),
                FOREIGN KEY (dinner_id) REFERENCES recipes(id)
            );
            """
        )
        conn.commit()


def row_to_recipe_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "category": row["category"],
        "cook_time_min": row["cook_time_min"],
        "ingredients": json.loads(row["ingredients_json"]),
        "instructions": row["instructions"],
        "calories_per_serving": row["calories_per_serving"],
        "added_date": row["added_date"],
    }


def row_to_plan_dict(row: sqlite3.Row) -> dict[str, Any]:
    snacks_raw = row["snacks_ids_json"]
    snacks = json.loads(snacks_raw) if snacks_raw else []
    return {
        "date": row["date"],
        "breakfast_id": row["breakfast_id"],
        "lunch_id": row["lunch_id"],
        "dinner_id": row["dinner_id"],
        "snacks_ids": snacks,
    }


def copy_database(target: Path) -> None:
    source = get_db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
