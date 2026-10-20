.PHONY: up down test lint migrate shell makemigrations

up:
	docker compose up --build -d

down:
	docker compose down

test:
	docker compose run --rm web python -m pytest -v

lint:
	docker compose run --rm web ruff check .
	docker compose run --rm web ruff format --check .
	docker compose run --rm web import-linter

migrate:
	docker compose run --rm web python manage.py migrate

shell:
	docker compose run --rm web python manage.py shell

makemigrations:
	docker compose run --rm web python manage.py makemigrations

# Additional useful targets
logs:
	docker compose logs -f

db-shell:
	docker compose exec db psql -U presto -d presto

redis-cli:
	docker compose exec redis redis-cli