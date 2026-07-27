# Фудграм

Развёрнутый проект: [foodgram-12.duckdns.org](https://foodgram-12.duckdns.org)

«Фудграм» — сайт, на котором пользователи публикуют рецепты, добавляют
чужие рецепты в избранное и подписываются на публикации других авторов.
Зарегистрированным пользователям доступен сервис «Список покупок»: он
позволяет собрать список продуктов, которые нужно купить для приготовления
выбранных блюд, и скачать его файлом. У каждого рецепта есть короткая
ссылка вида `/s/<id>`.

## Стек

- Python 3.11, Django 4.2, Django REST Framework, Djoser
- PostgreSQL (SQLite — для локальной разработки)
- Gunicorn, Nginx
- Docker, Docker Compose, GitHub Actions
- React (готовый фронтенд в `frontend/`)

## Запуск проекта в контейнерах (продакшен)

1. Клонируйте репозиторий и перейдите в его папку:

   ```bash
   git clone https://github.com/Zloyslon1/foodgram.git
   cd foodgram
   ```

2. Создайте файл `.env` по образцу
   [.env.example](.env.example) — рядом с `docker-compose.production.yml`.

3. Запустите контейнеры:

   ```bash
   docker compose -f docker-compose.production.yml up -d
   ```

   Миграции и сбор статики выполняются автоматически при старте бэкенда.

4. Наполните базу продуктами и тегами и создайте суперпользователя:

   ```bash
   docker compose -f docker-compose.production.yml exec backend \
       python manage.py import_ingredients
   docker compose -f docker-compose.production.yml exec backend \
       python manage.py import_tags
   docker compose -f docker-compose.production.yml exec backend \
       python manage.py createsuperuser
   ```

Сайт будет доступен на 80 порту, документация API —
[/api/docs/](https://foodgram-12.duckdns.org/api/docs/).

При пуше в ветку `main` GitHub Actions автоматически: проверяет код
линтером, собирает и публикует образы на Docker Hub, разворачивает проект
на сервере и присылает уведомление в Telegram. Необходимые секреты
репозитория: `DOCKER_USERNAME`, `DOCKER_PASSWORD`, `HOST`, `USER`,
`SSH_KEY`, `SSH_PASSPHRASE`, `TELEGRAM_TO`, `TELEGRAM_TOKEN`.

## Локальный запуск бэкенда (без Docker)

1. Клонируйте репозиторий и перейдите в его папку:

   ```bash
   git clone https://github.com/Zloyslon1/foodgram.git
   cd foodgram
   ```

2. Создайте виртуальное окружение и установите зависимости:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r backend/requirements.txt
   ```

3. Запустите сервер разработки:

   ```bash
   cd backend
   echo -e "USE_SQLITE=True\nDEBUG=True" > .env
   python manage.py migrate
   python manage.py import_ingredients
   python manage.py import_tags
   python manage.py createsuperuser
   python manage.py runserver
   ```

API поднимется на
[127.0.0.1:8000/api/](http://127.0.0.1:8000/api/). Для просмотра
спецификации и фронтенда выполните `docker compose up` из папки `infra/` —
фронт и Redoc будут на [localhost](http://localhost) и
[localhost/api/docs/](http://localhost/api/docs/).

Юнит- и интеграционные тесты API (pytest, 86 шт.):

```bash
cd backend
pytest
```

Проверка API готовой Postman-коллекцией — см.
[postman_collection/README.md](postman_collection/README.md)
(перед повторным прогоном: `bash postman_collection/clear_db.sh`).

## Наполнение базы

Обе команды импорта читают json-фикстуры из `backend/data/` и безопасны
при повторном запуске:

- `python manage.py import_ingredients` — ~2200 продуктов из
  `ingredients.json`;
- `python manage.py import_tags` — теги из `tags.json`.

Тестовые рецепты создаются через админ-зону `/admin/`.

## Автор

Бэкенд — Иван Кононенко:
[GitHub](https://github.com/Zloyslon1),
[почта](mailto:zl0y.slon@yandex.ru).

Фронтенд и спецификация API — Яндекс Практикум.
