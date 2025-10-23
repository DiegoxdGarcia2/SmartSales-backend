# Usar una imagen base de Python slim
FROM python:3.13-slim

# Establecer variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Crear y establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para PostgreSQL y compilación
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copiar el código de la aplicación
COPY . /app/

# Exponer el puerto que usará Gunicorn (Render lo inyectará como $PORT)
EXPOSE 8000

# Copiar y dar permisos al script de inicio
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

# Usar run.sh como comando de inicio
CMD ["/app/run.sh"]
