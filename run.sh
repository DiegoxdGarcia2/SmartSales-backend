#!/bin/bash

echo "🔄 Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

echo "🚀 Iniciando Gunicorn..."
exec gunicorn smartsales_backend.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-2} \
    --timeout 120 \
    --graceful-timeout 120 \
    --keep-alive 5 \
    --log-level info
