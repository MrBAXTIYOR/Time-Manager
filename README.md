# Time Management System (Google Calendar-inspired backend)

FastAPI · SQLAlchemy 2.0 async · MySQL 8 · Redis · Alembic · Pytest · Docker Compose · uv

## Quick start (Docker)
    cp .env.example .env            # then change the passwords
    docker compose up --build -d
    docker compose exec api alembic upgrade head
    open http://localhost:8000/docs

## Without Docker for the API (infra still in Docker)
    docker compose up -d mysql redis
    # in .env: MYSQL_HOST=localhost, REDIS_URL=redis://localhost:6379/0
    uv sync && uv run alembic upgrade head && make run

## Quality gates
    make test-unit    # no infrastructure needed
    make test         # unit + integration (needs mysql + redis; uses DB `tms_test`)
    make lint && make typecheck

## Migrations
    make revision m="add users"     # autogenerate, then REVIEW the file
    make migrate
