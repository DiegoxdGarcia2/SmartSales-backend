# Usar una imagen base de Python slim
FROM python:3.13-slim

# Establecer variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Crear y establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para PostgreSQL, compilación y WeasyPrint (PDFs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copiar el código de la aplicación primero
COPY . /app/

# DEBUG: Listar archivos para verificar
RUN ls -la /app/ && ls -la /app/requirements.txt || echo "requirements.txt NO EXISTE"

# Instalar dependencias de Python
RUN pip install --upgrade pip && pip install -r requirements.txt

# Exponer el puerto que usará Gunicorn (Render lo inyectará como $PORT)
EXPOSE 8000

# Dar permisos al script de inicio
RUN chmod +x /app/run.sh

# Usar run.sh como comando de inicio
CMD ["/app/run.sh"]
