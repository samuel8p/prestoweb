FROM python:3.12-slim

# Install uv (project dependency resolver)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /app

# Copy the whole project
COPY . .

# Install required packages with Django 5.x constraint
RUN pip install --no-cache-dir \
    "Django>=5.2,<6" \
    "djangorestframework>=3.14" \
    "drf-spectacular>=0.30" \
    "djangorestframework-simplejwt>=5.3" \
    "pytest>=7.0" \
    "pytest-django>=4.0" \
    "factory-boy>=3.0" \
    "ruff>=0.1.0" \
    "import-linter>=2.0" \
    "psycopg2-binary>=2.9" \
    "python-dotenv>=1.0" \
    "argon2-cffi>=21.0.0" \
    "gunicorn>=22.0.0" \
    "celery>=5.3.0" \
    "redis>=5.0.0" \
    "dj-database-url>=2.2.0"

EXPOSE 8000

# Migrations + Gunicorn (docker-compose overrides the CMD to run migrations first)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]