"""Вспомогательные функции ввода."""

from datetime import datetime


def read_line(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    if not value and default is not None:
        return default
    return value


def read_int(prompt: str, default: int | None = None) -> int:
    while True:
        raw = read_line(prompt, str(default) if default is not None else None)
        if not raw and default is not None:
            return default
        try:
            return int(raw)
        except ValueError:
            print("Введите целое число.")


def read_float_optional(prompt: str) -> float | None:
    raw = read_line(prompt + " (Enter — пропустить)", None)
    if not raw:
        return None
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        print("Некорректное число, калории не будут сохранены.")
        return None


def read_yes_no(prompt: str) -> bool:
    while True:
        raw = read_line(prompt + " (д/н)", None).lower()
        if raw in ("д", "да", "y", "yes"):
            return True
        if raw in ("н", "нет", "n", "no"):
            return False
        print("Ответьте «д» или «н».")


def read_multiline(prompt: str) -> str:
    print(prompt)
    print("(пустая строка — завершить ввод)")
    lines = []
    while True:
        line = input()
        if not line.strip():
            break
        lines.append(line)
    return "\n".join(lines)


def read_ingredients() -> list[str]:
    print("Ингредиенты (формат: яйцо: 2 шт.), пустая строка — конец:")
    lines = []
    while True:
        line = input("> ").strip()
        if not line:
            break
        lines.append(line)
    return lines


def validate_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def read_date(prompt: str, default: str | None = None) -> str:
    while True:
        value = read_line(prompt, default)
        if validate_date(value):
            return value
        print("Формат даты: YYYY-MM-DD")
