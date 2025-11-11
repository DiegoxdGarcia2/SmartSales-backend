#!/bin/bash
# Script para ejecutar migraciones en Cloud Run Job

echo "🔄 Ejecutando migraciones de base de datos..."
python manage.py migrate --noinput

echo "✅ Migraciones completadas exitosamente"
