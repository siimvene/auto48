# auto48

An open car marketplace for the Estonian/Baltic market — a competitor to
[auto24.ee](https://www.auto24.ee).

- **Backend:** FastAPI · Python 3.12+ · async SQLAlchemy 2.0 · Alembic
- **Frontend:** Nuxt 4 · Vue 3 (Composition API)
- **Standards:** shared development standards under [`.cursor/rules/`](.cursor/rules), distilled for
  AI agents in [`CLAUDE.md`](CLAUDE.md). Project memory via [memspec](.memspec).

## Quick start

### Backend

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn auto48.main:app --reload
```

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Example resource: `GET/POST /v1/listings`

Defaults to a local sqlite database (zero config). For real environments set
`AUTO48_DATABASE_URL` to a `postgresql+asyncpg://…` DSN and manage schema with Alembic:

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

### Local infrastructure (Docker)

Postgres+PostGIS, Redis, and MinIO are provided via Docker Compose for local development:

```bash
docker compose up -d
```

| Service | URL / address | Credentials |
|---------|--------------|-------------|
| Postgres (PostGIS) | `localhost:5432` db `auto48` | user `auto48` / pw `auto48` |
| Redis | `localhost:6379` | — |
| MinIO S3 API | `http://localhost:9000` | key `auto48` / secret `auto48secret` |
| MinIO console | `http://localhost:9001` | same credentials |

The `createbuckets` one-shot container automatically creates the `auto48-media` bucket with public download access once MinIO is healthy.

To use Postgres instead of the default SQLite, copy the commented-out vars from `.env.example` into `.env` after the containers are running.

### Tests & checks

```bash
pytest
ruff check src tests
mypy src
```

## Project structure

See [`CLAUDE.md`](CLAUDE.md) for the full layout and conventions, and
[`docs/implementation-plan.md`](docs/implementation-plan.md) for status and roadmap.

## License

TBD.
