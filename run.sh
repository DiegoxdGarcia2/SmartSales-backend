#!/bin/bash

PORT="${PORT:-8080}"

# Aplicar migraciones de base de datos
echo "� Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

echo "�🚀 Iniciando Gunicorn en puerto $PORT..."
exec gunicorn smartsales_backend.wsgi:application \
    --bind "0.0.0.0:$PORT" \
    --workers ${WEB_CONCURRENCY:-2} \
    --timeout 120 \
    --graceful-timeout 120 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
