"""Модуль планировщика питания."""

import json
from datetime import date, timedelta
from typing import Any

from database import get_connection, row_to_plan_dict
from recipes import fetch_recipe_by_id


def save_meal_plan(
    plan_date: str,
    breakfast_id: int | None,
    lunch_id: int | None,
    dinner_id: int | None,
    snacks_ids: list[int],
) -> None:
    snacks_json = json.dumps(snacks_ids, ensure_ascii=False)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO meal_plans (
                date, breakfast_id, lunch_id, dinner_id, snacks_ids_json
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                breakfast_id = excluded.breakfast_id,
                lunch_id = excluded.lunch_id,
                dinner_id = excluded.dinner_id,
                snacks_ids_json = excluded.snacks_ids_json
            """,
            (plan_date, breakfast_id, lunch_id, dinner_id, snacks_json),
        )
        conn.commit()


def fetch_plan_by_date(plan_date: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM meal_plans WHERE date = ?", (plan_date,)
        ).fetchone()
    if row is None:
        return None
    return row_to_plan_dict(row)


def fetch_plans_between(start_date: str, end_date: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM meal_plans
            WHERE date >= ? AND date <= ?
            ORDER BY date
            """,
            (start_date, end_date),
        ).fetchall()
    return list(map(row_to_plan_dict, rows))


def fetch_plans_last_days(days: int) -> list[dict[str, Any]]:
    end = date.today()
    start = end - timedelta(days=days - 1)
    return fetch_plans_between(start.isoformat(), end.isoformat())


def _collect_recipe_ids(plan: dict[str, Any]) -> list[int]:
    ids = []
    for key in ("breakfast_id", "lunch_id", "dinner_id"):
        value = plan.get(key)
        if value is not None:
            ids.append(value)
    ids.extend(plan.get("snacks_ids") or [])
    return ids


def summarize_day_plan(plan_date: str) -> dict[str, Any] | None:
    plan = fetch_plan_by_date(plan_date)
    if plan is None:
        return None

    recipe_ids = _collect_recipe_ids(plan)
    recipes = list(
        filter(
            None,
            map(fetch_recipe_by_id, recipe_ids),
        )
    )

    total_time = sum(map(lambda r: r["cook_time_min"], recipes))
    calories_list = list(
        map(
            lambda r: r["calories_per_serving"],
            filter(lambda r: r["calories_per_serving"] is not None, recipes),
        )
    )
    total_calories = sum(calories_list) if calories_list else None

    return {
        "date": plan_date,
        "plan": plan,
        "recipes": recipes,
        "total_cook_time_min": total_time,
        "total_calories": total_calories,
        "meals_count": len(recipes),
    }


def format_day_summary(summary: dict[str, Any]) -> str:
    lines = [f"=== План на {summary['date']} ==="]
    slots = [
        ("Завтрак", summary["plan"]["breakfast_id"]),
        ("Обед", summary["plan"]["lunch_id"]),
        ("Ужин", summary["plan"]["dinner_id"]),
    ]
    for label, recipe_id in slots:
        if recipe_id is None:
            lines.append(f"{label}: не выбран")
            continue
        recipe = fetch_recipe_by_id(recipe_id)
        if recipe:
            lines.append(f"{label}: {recipe['title']} ({recipe['cook_time_min']} мин)")
        else:
            lines.append(f"{label}: рецепт #{recipe_id} не найден")

    snack_ids = summary["plan"].get("snacks_ids") or []
    if snack_ids:
        lines.append("Перекусы:")
        for sid in snack_ids:
            recipe = fetch_recipe_by_id(sid)
            name = recipe["title"] if recipe else f"#{sid}"
            lines.append(f"  - {name}")

    lines.append(f"Общее время готовки: {summary['total_cook_time_min']} мин.")
    if summary["total_calories"] is not None:
        lines.append(f"Суммарная калорийность: {summary['total_calories']} ккал")
    else:
        lines.append("Суммарная калорийность: не рассчитана (нет данных)")
    return "\n".join(lines)


def format_plan_history(plans: list[dict[str, Any]]) -> str:
    if not plans:
        return "Планов за выбранный период нет."

    lines = ["История планов:"]
    for plan in plans:
        summary = summarize_day_plan(plan["date"])
        cal = summary["total_calories"] if summary else "?"
        time_val = summary["total_cook_time_min"] if summary else "?"
        lines.append(
            f"  {plan['date']}: блюд — {summary['meals_count'] if summary else 0}, "
            f"время — {time_val} мин, ккал — {cal}"
        )
    return "\n".join(lines)
