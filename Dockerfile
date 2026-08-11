FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# collectstatic needs settings to load, which requires a SECRET_KEY when
# DEBUG=False. This build-time value is never used to serve traffic - Fly
# injects the real DJANGO_SECRET_KEY secret at container runtime, which
# overrides it.
RUN DJANGO_SECRET_KEY=build-time-placeholder-not-used-at-runtime \
    python manage.py collectstatic --noinput

EXPOSE 8000

# Railway injects PORT at runtime; default to 8000 for local `docker run`.
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn metocore.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2"]
