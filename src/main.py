#!/usr/bin/env python3
"""CookBook — персональный кулинарный ассистент (консольное приложение)."""

import logging
import sys
from datetime import date
from pathlib import Path

from config import BASE_DIR
from data_management import (
    create_auto_backup,
    export_all_to_zip,
    import_from_zip,
)
from database import init_database
from logger_setup import setup_logging
from meal_planner import (
    fetch_plans_last_days,
    format_day_summary,
    format_plan_history,
    save_meal_plan,
    summarize_day_plan,
)
from recipes import (
    add_recipe,
    apply_recipe_filters,
    delete_recipe,
    fetch_all_recipes,
    fetch_recipe_by_id,
    format_recipe_card,
    format_recipe_short,
    parse_ingredients_lines,
    sort_recipes,
    update_recipe,
)
from utils import (
    read_date,
    read_float_optional,
    read_ingredients,
    read_int,
    read_line,
    read_multiline,
    read_yes_no,
)

logger = setup_logging()


def pause() -> None:
    input("\nНажмите Enter...")


def choose_recipe_id(prompt: str) -> int | None:
    recipes = fetch_all_recipes()
    if not recipes:
        print("Список рецептов пуст. Сначала добавьте рецепт.")
        return None
    for recipe in recipes:
        print(format_recipe_short(recipe))
    while True:
        raw = read_line(prompt)
        try:
            recipe_id = int(raw)
        except ValueError:
            print("Введите числовой ID.")
            continue
        if fetch_recipe_by_id(recipe_id):
            return recipe_id
        print("Рецепт с таким ID не найден.")


def menu_add_recipe() -> None:
    try:
        title = read_line("Название")
        if not title:
            print("Название обязательно.")
            return
        category = read_line("Категория (завтрак, суп, выпечка...)")
        cook_time = read_int("Время приготовления (мин)")
        if cook_time < 0:
            print("Время не может быть отрицательным.")
            return
        ingredients = read_ingredients()
        if not ingredients:
            print("Добавьте хотя бы один ингредиент.")
            return
        instructions = read_multiline("Пошаговая инструкция")
        calories = read_float_optional("Калорийность на порцию")
        added = read_date("Дата добавления", date.today().isoformat())

        recipe_id = add_recipe(
            title, category, cook_time, ingredients, instructions, calories, added
        )
        logger.info("Добавлен рецепт id=%s: %s", recipe_id, title)
        print(f"Рецепт сохранён (ID {recipe_id}).")
    except Exception as exc:
        logger.exception("Ошибка при добавлении рецепта: %s", exc)
        print(f"Ошибка: {exc}")


def menu_list_recipes() -> None:
    try:
        recipes = fetch_all_recipes()
        if not recipes:
            print("Рецептов пока нет.")
            return

        print("\n--- Фильтры (Enter — пропустить) ---")
        category = read_line("Категория", None) or None
        max_time_raw = read_line("Макс. время (мин, напр. 30)", None)
        max_time = int(max_time_raw) if max_time_raw else None
        only_cal = read_yes_no("Только с указанной калорийностью?")

        filtered = apply_recipe_filters(
            recipes,
            category=category,
            max_time=max_time,
            only_with_calories=only_cal,
        )

        sort_by = read_line(
            "Сортировка: title / time / calories / date", "title"
        )
        filtered = sort_recipes(filtered, by=sort_by)

        print(f"\nНайдено: {len(filtered)}")
        for recipe in filtered:
            print(format_recipe_short(recipe))
    except Exception as exc:
        logger.exception("Ошибка списка рецептов: %s", exc)
        print(f"Ошибка: {exc}")


def menu_view_recipe() -> None:
    try:
        recipe_id = choose_recipe_id("ID рецепта для просмотра")
        if recipe_id is None:
            return
        recipe = fetch_recipe_by_id(recipe_id)
        if recipe:
            print("\n" + format_recipe_card(recipe))
    except Exception as exc:
        logger.exception("Ошибка просмотра: %s", exc)
        print(f"Ошибка: {exc}")


def menu_edit_recipe() -> None:
    try:
        recipe_id = choose_recipe_id("ID рецепта для редактирования")
        if recipe_id is None:
            return
        recipe = fetch_recipe_by_id(recipe_id)
        if not recipe:
            return

        print("Оставьте поле пустым, чтобы не менять.")
        fields = {}
        title = read_line("Название", recipe["title"])
        if title != recipe["title"]:
            fields["title"] = title

        category = read_line("Категория", recipe["category"])
        if category != recipe["category"]:
            fields["category"] = category

        time_raw = read_line(
            "Время (мин)", str(recipe["cook_time_min"])
        )
        if time_raw and int(time_raw) != recipe["cook_time_min"]:
            fields["cook_time_min"] = int(time_raw)

        if read_yes_no("Изменить ингредиенты?"):
            fields["ingredients"] = read_ingredients()

        if read_yes_no("Изменить инструкцию?"):
            fields["instructions"] = read_multiline("Новая инструкция")

        cal_raw = read_line(
            "Калории (Enter — не менять)",
            str(recipe["calories_per_serving"] or ""),
        )
        if cal_raw:
            fields["calories_per_serving"] = float(cal_raw.replace(",", "."))

        if fields and update_recipe(recipe_id, fields):
            logger.info("Обновлён рецепт id=%s", recipe_id)
            print("Рецепт обновлён.")
        else:
            print("Изменений нет.")
    except Exception as exc:
        logger.exception("Ошибка редактирования: %s", exc)
        print(f"Ошибка: {exc}")


def menu_delete_recipe() -> None:
    try:
        recipe_id = choose_recipe_id("ID рецепта для удаления")
        if recipe_id is None:
            return
        if read_yes_no("Удалить рецепт?"):
            if delete_recipe(recipe_id):
                logger.info("Удалён рецепт id=%s", recipe_id)
                print("Рецепт удалён.")
            else:
                print("Не удалось удалить.")
    except Exception as exc:
        logger.exception("Ошибка удаления: %s", exc)
        print(f"Ошибка: {exc}")


def menu_create_meal_plan() -> None:
    try:
        plan_date = read_date("Дата плана", date.today().isoformat())
        print("Выберите рецепты для приёмов пищи (Enter — пропустить слот).")

        breakfast = None
        if read_yes_no("Добавить завтрак?"):
            breakfast = choose_recipe_id("ID завтрака")

        lunch = None
        if read_yes_no("Добавить обед?"):
            lunch = choose_recipe_id("ID обеда")

        dinner = None
        if read_yes_no("Добавить ужин?"):
            dinner = choose_recipe_id("ID ужина")

        snacks = []
        while read_yes_no("Добавить перекус?"):
            sid = choose_recipe_id("ID перекуса")
            if sid:
                snacks.append(sid)

        save_meal_plan(plan_date, breakfast, lunch, dinner, snacks)
        logger.info("Сохранён план питания на %s", plan_date)

        summary = summarize_day_plan(plan_date)
        if summary:
            print("\n" + format_day_summary(summary))
    except Exception as exc:
        logger.exception("Ошибка планировщика: %s", exc)
        print(f"Ошибка: {exc}")


def menu_day_summary() -> None:
    try:
        plan_date = read_date("Дата", date.today().isoformat())
        summary = summarize_day_plan(plan_date)
        if summary:
            print("\n" + format_day_summary(summary))
        else:
            print("План на эту дату не найден.")
    except Exception as exc:
        logger.exception("Ошибка сводки: %s", exc)
        print(f"Ошибка: {exc}")


def menu_plan_history() -> None:
    try:
        period = read_line("Период: week / month", "week")
        days = 7 if period.startswith("w") else 30
        plans = fetch_plans_last_days(days)
        print(format_plan_history(plans))
    except Exception as exc:
        logger.exception("Ошибка истории: %s", exc)
        print(f"Ошибка: {exc}")


def menu_export() -> None:
    try:
        path_str = read_line(
            "Путь к ZIP (Enter — автоимя в папке проекта)", None
        )
        path = Path(path_str) if path_str else None
        if path and not path.is_absolute():
            path = BASE_DIR / path
        archive = export_all_to_zip(path)
        logger.info("Экспорт в %s", archive)
        print(f"Экспорт выполнен: {archive}")
    except Exception as exc:
        logger.exception("Ошибка экспорта: %s", exc)
        print(f"Ошибка экспорта: {exc}")


def menu_import() -> None:
    try:
        path_str = read_line("Путь к ZIP-архиву")
        if not path_str:
            print("Путь не указан.")
            return
        path = Path(path_str)
        if not path.is_absolute():
            path = BASE_DIR / path
        import_from_zip(path)
        logger.info("Импорт из %s", path)
        print("Импорт завершён.")
    except Exception as exc:
        logger.exception("Ошибка импорта: %s", exc)
        print(f"Ошибка импорта: {exc}")


def menu_backup() -> None:
    try:
        backup_path = create_auto_backup()
        logger.info("Резервная копия: %s", backup_path)
        print(f"Бэкап создан: {backup_path}")
    except Exception as exc:
        logger.exception("Ошибка бэкапа: %s", exc)
        print(f"Ошибка: {exc}")


def print_main_menu() -> None:
    print(
        """
╔══════════════════════════════════════╗
║         CookBook — меню              ║
╠══════════════════════════════════════╣
║  РЕЦЕПТЫ                             ║
║   1. Добавить рецепт                 ║
║   2. Список рецептов (фильтры)       ║
║   3. Карточка рецепта                ║
║   4. Редактировать рецепт            ║
║   5. Удалить рецепт                  ║
║  ПЛАН ПИТАНИЯ                        ║
║   6. Создать/обновить план дня       ║
║   7. Сводка по дню                   ║
║   8. История планов (неделя/месяц)   ║
║  ДАННЫЕ                              ║
║   9. Экспорт в ZIP                   ║
║  10. Импорт из ZIP                   ║
║  11. Резервная копия БД              ║
║   0. Выход                           ║
╚══════════════════════════════════════╝
"""
    )


def main() -> None:
    try:
        init_database()
        create_auto_backup()
        logger.info("Запуск CookBook")
    except Exception as exc:
        print(f"Не удалось инициализировать приложение: {exc}")
        sys.exit(1)

    actions = {
        "1": menu_add_recipe,
        "2": menu_list_recipes,
        "3": menu_view_recipe,
        "4": menu_edit_recipe,
        "5": menu_delete_recipe,
        "6": menu_create_meal_plan,
        "7": menu_day_summary,
        "8": menu_plan_history,
        "9": menu_export,
        "10": menu_import,
        "11": menu_backup,
    }

    while True:
        print_main_menu()
        choice = read_line("Выбор", None)
        if choice == "0":
            logger.info("Завершение работы")
            print("До встречи!")
            break
        action = actions.get(choice)
        if action:
            action()
            pause()
        else:
            print("Неверный пункт меню.")


if __name__ == "__main__":
    main()
