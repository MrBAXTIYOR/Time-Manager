.PHONY: up down run test test-unit lint typecheck migrate revision
up:        ; docker compose up --build -d
down:      ; docker compose down
run:       ; uv run uvicorn app.main:create_app --factory --reload
test:      ; uv run pytest
test-unit: ; uv run pytest -m "not integration"
lint:      ; uv run ruff check . && uv run ruff format --check .
typecheck: ; uv run mypy app
migrate:   ; uv run alembic upgrade head
revision:  ; uv run alembic revision --autogenerate -m "$(m)"
