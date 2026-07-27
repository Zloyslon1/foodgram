#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput
mkdir -p /backend_static/static
cp -r /app/collected_static/. /backend_static/static/

exec gunicorn --bind 0.0.0.0:8000 foodgram_backend.wsgi
