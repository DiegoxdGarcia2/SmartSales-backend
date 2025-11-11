#!/bin/bash

# NO salir si falla un comando (para que migraciones/collectstatic no bloqueen)
set +e

# Ejecutar migraciones y collectstatic en background
(
    echo "🔄 Aplicando migraciones de base de datos en background..."
    python manage.py migrate --noinput 2>&1 | head -20
    echo "📦 Recolectando archivos estáticos en background..."
    python manage.py collectstatic --noinput 2>&1 | head -20
    echo "✅ Tareas de inicialización completadas"
) &

# Guardar el PID del proceso background
INIT_PID=$!

echo "🚀 Iniciando Gunicorn inmediatamente..."
# Cloud Run/Render inyectan la variable $PORT
# Timeout aumentado para evitar worker timeouts
exec gunicorn smartsales_backend.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-2} \
    --timeout 120 \
    --graceful-timeout 120 \
    --keep-alive 5 \
    --log-level info
