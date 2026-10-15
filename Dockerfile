# syntax=docker/dockerfile:1
#
# Dev workflow: manage deps with Poetry, then regenerate requirements.txt:
#   poetry export --without-hashes --only main -o requirements.txt

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN groupadd --system app && useradd --system --gid app --home /app app \
    && install -d -o app -g app /app /app/media

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=app:app . .

# static files are collected into the image, so the running container never needs write access to /app
RUN SECRET_KEY=build-only DATABASE_URL=sqlite:////tmp/build.db python manage.py collectstatic --noinput

USER app

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
