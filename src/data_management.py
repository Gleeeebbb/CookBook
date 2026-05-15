"""Экспорт, импорт и резервное копирование."""

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from config import BASE_DIR
from database import copy_database, get_connection, init_database, row_to_plan_dict, row_to_recipe_dict


RECIPES_JSON = "recipes.json"
PLANS_JSON = "meal_plans.json"
DB_BACKUP_NAME = "cookbook_backup.sqlite"


def backups_dir() -> Path:
    path = BASE_DIR / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_auto_backup() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    target = backups_dir() / f"backup_{timestamp}.sqlite"
    copy_database(target)
    return target


def export_all_to_zip(archive_path: Path | None = None) -> Path:
    if archive_path is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = BASE_DIR / f"cookbook_export_{stamp}.zip"

    with get_connection() as conn:
        recipe_rows = conn.execute("SELECT * FROM recipes").fetchall()
        plan_rows = conn.execute("SELECT * FROM meal_plans").fetchall()

    recipes = list(map(row_to_recipe_dict, recipe_rows))
    plans = list(map(row_to_plan_dict, plan_rows))

    temp_dir = BASE_DIR / ".export_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        recipes_file = temp_dir / RECIPES_JSON
        plans_file = temp_dir / PLANS_JSON
        db_file = temp_dir / DB_BACKUP_NAME

        recipes_file.write_text(
            json.dumps(recipes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        plans_file.write_text(
            json.dumps(plans, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        copy_database(db_file)

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(recipes_file, RECIPES_JSON)
            zf.write(plans_file, PLANS_JSON)
            zf.write(db_file, DB_BACKUP_NAME)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return archive_path


def _import_recipes_from_json(recipes: list[dict]) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM recipes")
        for recipe in recipes:
            conn.execute(
                """
                INSERT INTO recipes (
                    id, title, category, cook_time_min, ingredients_json,
                    instructions, calories_per_serving, added_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recipe["id"],
                    recipe["title"],
                    recipe["category"],
                    recipe["cook_time_min"],
                    json.dumps(recipe["ingredients"], ensure_ascii=False),
                    recipe["instructions"],
                    recipe.get("calories_per_serving"),
                    recipe["added_date"],
                ),
            )
        conn.commit()


def _import_plans_from_json(plans: list[dict]) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM meal_plans")
        for plan in plans:
            snacks = plan.get("snacks_ids") or []
            conn.execute(
                """
                INSERT INTO meal_plans (
                    date, breakfast_id, lunch_id, dinner_id, snacks_ids_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    plan["date"],
                    plan.get("breakfast_id"),
                    plan.get("lunch_id"),
                    plan.get("dinner_id"),
                    json.dumps(snacks, ensure_ascii=False),
                ),
            )
        conn.commit()


def import_from_zip(archive_path: Path) -> None:
    if not archive_path.exists():
        raise FileNotFoundError(f"Архив не найден: {archive_path}")

    extract_dir = BASE_DIR / ".import_tmp"
    extract_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(extract_dir)

        recipes_file = extract_dir / RECIPES_JSON
        plans_file = extract_dir / PLANS_JSON
        db_file = extract_dir / DB_BACKUP_NAME

        if db_file.exists():
            from config import get_db_path

            target_db = get_db_path()
            target_db.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(db_file, target_db)
            init_database()
            return

        if not recipes_file.exists():
            raise ValueError("В архиве нет recipes.json")

        recipes = json.loads(recipes_file.read_text(encoding="utf-8"))
        _import_recipes_from_json(recipes)

        if plans_file.exists():
            plans = json.loads(plans_file.read_text(encoding="utf-8"))
            _import_plans_from_json(plans)
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)
