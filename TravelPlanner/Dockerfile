FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install deps first so this layer is cached between code changes.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# DB will live under /app/data when the volume is mounted.
RUN mkdir -p /app/data

EXPOSE 8000

# Apply migrations on container start, then serve with gunicorn.
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn TravelPlanner.wsgi:application --bind 0.0.0.0:8000 --workers 2"]