# CookBook — персональный кулинарный ассистент

Консольное приложение на Python (вариант 7 практикума).  
Управление рецептами, планирование питания, SQLite, экспорт/импорт ZIP.

## Требования

- Python 3.10+
- Зависимости из `requirements.txt`

## Установка

```bash
cd cookbook
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Запуск

```bash
cd src
python main.py
```

## Структура

```
cookbook/
├── src/
│   ├── main.py           # меню и точка входа
│   ├── config.py         # .env
│   ├── database.py       # SQLite
│   ├── recipes.py        # рецепты, filter/lambda/замыкания
│   ├── meal_planner.py   # планы питания
│   ├── data_management.py # экспорт/импорт/бэкапы
│   ├── logger_setup.py
│   └── utils.py
├── backups/              # автокопии БД
├── data/                 # cookbook.sqlite (создаётся автоматически)
├── .env.example
├── requirements.txt
└── README.md
```

## Функции

- CRUD рецептов с фильтрацией (категория, время ≤ N мин, калории)
- План на день: завтрак, обед, ужин, перекусы + сводка времени и ккал
- История планов за 7 или 30 дней
- Экспорт ZIP: `recipes.json`, `meal_plans.json`, копия `.sqlite`
- Импорт из ZIP
- Логи в `app.log`, настройки в `.env`

## Git (для сдачи)

Рекомендуемый workflow из задания:

1. Создать репозиторий на GitHub
2. Ветки: `feature/recipe-manager`, `feature/meal-planner`
3. Минимум 3 Pull Request в `main` (Squash and Merge)
4. Защитить ветку `main` от прямых коммитов
