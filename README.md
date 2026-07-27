# Фудграм

**Адрес сервера:** https://foodgram-12.duckdns.org

«Фудграм» — сайт, на котором пользователи публикуют рецепты, добавляют
чужие рецепты в избранное и подписываются на публикации других авторов.
Зарегистрированным пользователям доступен сервис «Список покупок»: он
позволяет собрать список продуктов, которые нужно купить для приготовления
выбранных блюд, и скачать его файлом. У каждого рецепта есть короткая
ссылка вида `/s/<код>`.

## Стек

- Python 3.11, Django 4.2, Django REST Framework, Djoser
- PostgreSQL (SQLite — для локальной разработки)
- Gunicorn, Nginx
- Docker, Docker Compose, GitHub Actions
- React (готовый фронтенд в `frontend/`)

## Запуск проекта в контейнерах (продакшен)

1. Скопируйте на сервер `docker-compose.production.yml` и создайте рядом
   файл `.env` по образцу `.env.example`:

   ```bash
   scp docker-compose.production.yml .env <user>@<host>:foodgram/
   ```

2. Запустите контейнеры:

   ```bash
   docker compose -f docker-compose.production.yml up -d
   ```

   Миграции и сбор статики выполняются автоматически при старте бэкенда.

3. Наполните базу ингредиентами и создайте суперпользователя:

   ```bash
   docker compose -f docker-compose.production.yml exec backend \
       python manage.py import_ingredients
   docker compose -f docker-compose.production.yml exec backend \
       python manage.py createsuperuser
   ```

4. Создайте теги в админ-зоне: `http://<host>/admin/` → Теги
   (например, «Завтрак/breakfast», «Обед/lunch», «Ужин/dinner»).

Сайт будет доступен на 80 порту, документация API — по адресу
`http://<host>/api/docs/`.

При пуше в ветку `main` GitHub Actions автоматически: проверяет код
линтером, собирает и публикует образы на Docker Hub, разворачивает проект
на сервере и присылает уведомление в Telegram. Необходимые секреты
репозитория: `DOCKER_USERNAME`, `DOCKER_PASSWORD`, `HOST`, `USER`,
`SSH_KEY`, `SSH_PASSPHRASE`, `TELEGRAM_TO`, `TELEGRAM_TOKEN`.

## Локальный запуск бэкенда (без Docker)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

cd backend
echo -e "USE_SQLITE=True\nDEBUG=True" > .env
python manage.py migrate
python manage.py import_ingredients
python manage.py createsuperuser
python manage.py runserver
```

API поднимется на `http://127.0.0.1:8000/api/`. Для просмотра
спецификации и фронтенда выполните `docker compose up` из папки `infra/` —
фронт и Redoc будут на `http://localhost` и `http://localhost/api/docs/`.

Юнит- и интеграционные тесты API (pytest, 86 шт.):

```bash
cd backend
pytest
```

Проверка API готовой Postman-коллекцией — см.
[postman_collection/README.md](postman_collection/README.md)
(перед повторным прогоном: `bash postman_collection/clear_db.sh`).

## Наполнение базы

- `python manage.py import_ingredients` — загружает ~2200 ингредиентов из
  `data/ingredients.csv` (повторный запуск безопасен);
- теги и тестовые рецепты создаются через админ-зону `/admin/`.

## Автор

Бэкенд: [Zloyslon1](https://github.com/Zloyslon1).
Фронтенд и спецификация API — Яндекс Практикум.
