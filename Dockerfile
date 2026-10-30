FROM python:3.11-slim

WORKDIR /app

# Primero las dependencias, para aprovechar la cache de capas de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# La aplicacion y el modelo viajan dentro de la imagen
COPY app/ ./app/
COPY model/ ./model/

ENV PYTHONUNBUFFERED=1

# Cloud Run inyecta el puerto en la variable PORT
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
