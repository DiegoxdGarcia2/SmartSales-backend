#!/bin/bash

# Salir inmediatamente si un comando falla
set -e

echo "🔄 Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

echo "🧠 Analizando sentimiento de reseñas..."
python manage.py analyze_existing_sentiments || echo "⚠️ Warning: Sentiment analysis failed or no reviews to analyze"

echo "📦 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

echo "🚀 Iniciando Gunicorn..."
# Render inyecta la variable $PORT
exec gunicorn smartsales_backend.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-4}
