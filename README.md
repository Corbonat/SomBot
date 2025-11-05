# Varshеr & PredskazBot Skeleton

Базовый каркас для основного Telegram-бота Varshеr и PredskazBot по ТЗ.

## Сервисы

- `app/` — основной бот на aiogram 3.
- `pred/` — PredskazBot.
- `worker/` — фоновые задачи (разогрев кэша и т.п.).

## Быстрый старт

```bash
cp .env.example .env
# заполните токены и эндпойнты

docker compose up --build
```

Локально без Docker:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
python -m app.main
```

PredskazBot:

```bash
python -m pred.main
```

Worker:

```bash
python -m worker.main
```

## Структура

- `app/core` — конфиг, логирование, подключения.
- `app/handlers` — хендлеры меню, курсов, AML, лидов.
- `app/rates` — модели, сервисы и провайдеры курсов.
- `app/services` — доменные сервисы (AML, лиды).
- `pred/services` — генерация фраз и автопост.
- `migrations` — Alembic (пусто, подготовлено).
- `tests` — каталог для pytest.

## Дальнейшие шаги

1. Реализовать интеграции с Bybit, Rapira, Grinex.
2. Добавить модели/ORM и миграции Alembic.
3. Настроить хранение текстов/локализаций и inline-режим.
4. Расширить PredskazBot: автопостинг, фильтры, opt-in.
5. Подключить observability (OpenTelemetry, метрики).
