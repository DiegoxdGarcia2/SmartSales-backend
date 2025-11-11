#!/bin/bash

# ESTRATEGIA: Iniciar Gunicorn INMEDIATAMENTE sin esperar nada
# Las migraciones y collectstatic se ejecutarán después manualmente o en otro job

echo "🚀 Iniciando Gunicorn inmediatamente (sin migraciones ni collectstatic)..."

# Iniciar Gunicorn directamente
exec gunicorn smartsales_backend.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-2} \
    --timeout 120 \
    --graceful-timeout 120 \
    --keep-alive 5 \
    --log-level info
