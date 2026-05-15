"""Модуль управления рецептами."""

import json
from datetime import date
from typing import Any, Callable

from database import get_connection, row_to_recipe_dict


def create_category_filter(category: str) -> Callable[[dict], bool]:
    """Фабрика фильтров по категории (замыкание)."""
    return lambda recipe: recipe["category"].lower() == category.lower()


def create_max_time_filter(max_minutes: int) -> Callable[[dict], bool]:
    return lambda recipe: recipe["cook_time_min"] <= max_minutes


def create_has_calories_filter() -> Callable[[dict], bool]:
    return lambda recipe: recipe["calories_per_serving"] is not None


def fetch_all_recipes() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM recipes ORDER BY added_date DESC, title"
        ).fetchall()
    return list(map(row_to_recipe_dict, rows))


def fetch_recipe_by_id(recipe_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
        ).fetchone()
    if row is None:
        return None
    return row_to_recipe_dict(row)


def parse_ingredients_lines(lines: list[str]) -> list[str]:
    cleaned = list(
        map(lambda line: line.strip(), filter(lambda s: s.strip(), lines))
    )
    return cleaned


def add_recipe(
    title: str,
    category: str,
    cook_time_min: int,
    ingredients: list[str],
    instructions: str,
    calories_per_serving: float | None,
    added_date: str | None = None,
) -> int:
    if added_date is None:
        added_date = date.today().isoformat()

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO recipes (
                title, category, cook_time_min, ingredients_json,
                instructions, calories_per_serving, added_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title.strip(),
                category.strip(),
                cook_time_min,
                json.dumps(ingredients, ensure_ascii=False),
                instructions.strip(),
                calories_per_serving,
                added_date,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_recipe(recipe_id: int, fields: dict[str, Any]) -> bool:
    allowed = {
        "title",
        "category",
        "cook_time_min",
        "ingredients",
        "instructions",
        "calories_per_serving",
        "added_date",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False

    columns = []
    values = []
    for key, value in updates.items():
        if key == "ingredients":
            columns.append("ingredients_json = ?")
            values.append(json.dumps(value, ensure_ascii=False))
        else:
            columns.append(f"{key} = ?")
            values.append(value)

    values.append(recipe_id)
    sql = f"UPDATE recipes SET {', '.join(columns)} WHERE id = ?"

    with get_connection() as conn:
        cursor = conn.execute(sql, values)
        conn.commit()
        return cursor.rowcount > 0


def delete_recipe(recipe_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        conn.commit()
        return cursor.rowcount > 0


def filter_recipes(
    recipes: list[dict[str, Any]],
    predicate: Callable[[dict], bool],
) -> list[dict[str, Any]]:
    return list(filter(predicate, recipes))


def apply_recipe_filters(
    recipes: list[dict[str, Any]],
    category: str | None = None,
    max_time: int | None = None,
    only_with_calories: bool = False,
) -> list[dict[str, Any]]:
    result = recipes
    if category:
        result = filter_recipes(result, create_category_filter(category))
    if max_time is not None:
        result = filter_recipes(result, create_max_time_filter(max_time))
    if only_with_calories:
        result = filter_recipes(result, create_has_calories_filter())
    return result


def sort_recipes(
    recipes: list[dict[str, Any]],
    by: str = "title",
    reverse: bool = False,
) -> list[dict[str, Any]]:
    key_map = {
        "title": lambda r: r["title"].lower(),
        "time": lambda r: r["cook_time_min"],
        "calories": lambda r: r["calories_per_serving"] or 0,
        "date": lambda r: r["added_date"],
    }
    key_fn = key_map.get(by, key_map["title"])
    return sorted(recipes, key=key_fn, reverse=reverse)


def format_recipe_card(recipe: dict[str, Any]) -> str:
    lines = [
        f"ID: {recipe['id']}",
        f"Название: {recipe['title']}",
        f"Категория: {recipe['category']}",
        f"Время: {recipe['cook_time_min']} мин.",
        f"Дата добавления: {recipe['added_date']}",
    ]
    if recipe["calories_per_serving"] is not None:
        lines.append(f"Калории на порцию: {recipe['calories_per_serving']}")
    else:
        lines.append("Калории: не указаны")

    lines.append("Ингредиенты:")
    lines.extend(map(lambda ing: f"  - {ing}", recipe["ingredients"]))
    lines.append("Инструкция:")
    lines.append(recipe["instructions"])
    return "\n".join(lines)


def format_recipe_short(recipe: dict[str, Any]) -> str:
    cal = (
        f"{recipe['calories_per_serving']} ккал"
        if recipe["calories_per_serving"] is not None
        else "ккал н/д"
    )
    return (
        f"[{recipe['id']}] {recipe['title']} | {recipe['category']} | "
        f"{recipe['cook_time_min']} мин | {cal}"
    )
