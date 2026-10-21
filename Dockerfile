FROM python:3.12-slim

# The application never runs as root: the web, worker and beat containers
# use this unprivileged user (audit M-3).
RUN groupadd --gid 1000 presto \
    && useradd --uid 1000 --gid 1000 --create-home --home-dir /home/presto \
        --shell /usr/sbin/nologin --no-log-init presto

# Install uv (project dependency resolver)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /app

# Copy the whole project
COPY --chown=presto:presto . .

# Install required packages with Django 5.x constraint
RUN pip install --no-cache-dir \
    "Django>=5.2,<6" \
    "djangorestframework>=3.14" \
    "drf-spectacular>=0.30" \
    "djangorestframework-simplejwt>=5.3" \
    "pytest>=7.0" \
    "pytest-django>=4.0" \
    "pytest-cov>=5.0" \
    "factory-boy>=3.0" \
    "ruff>=0.1.0" \
    "import-linter>=2.0" \
    "psycopg2-binary>=2.9" \
    "python-dotenv>=1.0" \
    "argon2-cffi>=21.0.0" \
    "gunicorn>=22.2.0" \
    "celery>=5.3.0" \
    "redis>=5.0.0" \
    "dj-database-url>=2.2.0"

# The beat writes its schedule file here. Creating the directory with the
# right owner makes the named volume inherit that ownership.
RUN mkdir -p /var/celerybeat && chown presto:presto /var/celerybeat

# In development the code arrives as a volume owned by the host user, so the
# container keeps every write (bytecode, pytest cache, coverage, linters) out
# of it.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest_cache" \
    COVERAGE_FILE=/tmp/.coverage \
    RUFF_CACHE_DIR=/tmp/ruff-cache

USER presto

EXPOSE 8000

# Migrations + Gunicorn (docker-compose overrides the CMD to run migrations first)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
