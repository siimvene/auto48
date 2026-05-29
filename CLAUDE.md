# auto48

Open car marketplace for the Estonian/Baltic market — an **auto24.ee competitor**.
**Stack:** FastAPI (Python 3.12+, async SQLAlchemy 2.0) backend + Nuxt 4 / Vue 3 frontend.

> Full, authoritative standards live in `.cursor/rules/**` (SMIT development standards).
> This file is the distilled, always-on summary for AI agents. When in doubt, read the
> matching `.mdc` rule. Do not contradict the rules.

## Before you start

- **Read `docs/agent-memory.md`** first; append corrections after fixing any mistake or
  deprecation (`.cursor/rules/common/agent-memory.mdc`).
- **`docs/implementation-plan.md`** is the single source of truth for status/roadmap
  (`.cursor/rules/ai-tools/project-context.mdc`). Check it before planning; update it after milestones.
- **memspec**: project memory lives in `.memspec/`. Search it first for operational/architectural
  facts: `memspec search <topic>`. A recorded decision outweighs inference from repo structure.

## Repository layout

```
src/auto48/            FastAPI backend package
  main.py              app factory + lifespan + RFC 7807 handler
  config.py            get_settings() factory (pydantic-settings, env AUTO48_*)
  db.py                async engine, session factory, get_db, Base
  api/dependencies.py  Annotated DI aliases (DbSession)
  api/routers/         thin routers (health, listings)
  models/              ORM models + Pydantic schemas
tests/                 pytest + pytest-asyncio (asyncio_mode=auto)
alembic/               async migrations (schema changes are a deploy step)
frontend/              Nuxt 4 / Vue 3 app (talks to backend over HTTP only)
docs/                  agent-memory.md, implementation-plan.md
.cursor/               rules, skills, commands, prompts, hooks
```

## Commands

```bash
# Backend (from repo root)
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
uvicorn auto48.main:app --reload        # http://localhost:8000  (GET /health, /docs)
pytest                                  # tests
ruff check src tests && mypy src        # lint + types
alembic revision --autogenerate -m "msg" && alembic upgrade head

# Frontend (from frontend/)
npm install && npm run dev              # http://localhost:3000
```

## Backend conventions (`.cursor/rules/python-fastapi/*`)

- `async def` for I/O paths; never block the event loop. Use `httpx` (async) for outbound HTTP.
- Type hints on every signature; modern syntax (`list[str]`, `X | None`). `mypy --strict` on `src/`.
- Pydantic models over raw dicts. RORO: object in, object out. Keep handlers thin; early returns.
- DI via `Annotated[..., Depends(...)]` aliases (e.g. `DbSession`), not repeated `Depends()`.
- Config via `get_settings()` factory — **no module-level settings singleton**, no external config files; env vars only.
- Lifespan over deprecated `@app.on_event`.
- SQLAlchemy 2.0 async: `select()` + `await session.execute/scalars/scalar`; never legacy `Session.query()`.
  Never build SQL from user strings — ORM/Core expressions bind parameters. Allowlist dynamic ORDER BY.
  Paginate with `limit`/`offset` + a separate `count()`. Avoid N+1 (`selectinload`/`joinedload`).
- Migrations run via Alembic as a deploy step — **never `create_all` on every startup** (the local-only
  bootstrap in `main.py` is gated on `environment == "local"`).

## API & integration (`.cursor/rules/common/integration-standards.mdc`)

- Resource URLs, kebab-case, versioned (`/v1/...`); no verbs in paths. Correct HTTP status codes.
- RFC 7807 Problem Details for errors (`application/problem+json`), include traceId/correlationId.
- OpenAPI is the contract; document all endpoints. HTTPS + OAuth 2.1/OIDC Bearer tokens in
  `Authorization` header — never tokens in URLs.

## Security (`.cursor/rules/common/security.mdc`)

- Validate all input; no sensitive detail in user-facing errors. Never log secrets/PII/tokens.
- Never store JWTs in browser storage. Health check endpoint required. Stateless services.

## Frontend (`.cursor/rules/typescript-{common,nuxt,vue}/*`)

- Vue 3 Composition API + `<script setup lang="ts">`. UI talks to backend over HTTP/JSON only —
  the backend never returns HTML/JS. API base via `runtimeConfig.public.apiBase`.

## Workflow

- Git: use `git --no-pager …` for log/diff/show (`.cursor/rules/ai-tools/git-commands.mdc`).
- Finishing substantial work: run the **quality-check** skill (code-simplifier → security-check →
  code-review → validation) in `.cursor/skills/quality-check/`.
- Code/comments in English; UTF-8; remove dead code; lock dependency versions.

<!-- memspec:init:start -->
## Memory (Memspec)

This project uses Memspec for structured memory. `.memspec/` is the canonical store for durable project knowledge.
Memspec is agent-operated, not human-curated with agent access.

### On session start
In Claude Code (and any harness supporting `SessionStart` hooks), the relevant active memories
are auto-injected at session start via `memspec context` — you should already see them.
As a fallback, run `memspec search` for context relevant to the task. Prefer active memories
over stale assumptions.

If the `memspec` command is not found (not on PATH) and no `memspec_*` MCP tools are available,
the CLI is still usable: it is a Node tool — run `npm link` in the memspec checkout to expose
`memspec`/`memspec-mcp`, or invoke it directly as `node <memspec-repo>/dist/cli.js <command>`.
Do not conclude the tool is missing without checking these.

### Retrieve before assuming
Before acting on an assumption about how this project works, search memspec. This applies to:
- **Operational knowledge** — deploy steps, server addresses, credential paths, established workflows
- **Architectural decisions** — tech stack choices, API design patterns, component boundaries, data models
- **Project conventions** — naming, file structure, testing strategy, code style rationale

Run `memspec search <topic>` before falling back to inference from repo structure or generic heuristics.
A recorded decision, fact, or procedure outweighs what the codebase appears to suggest — the memory captures *why*, the code only shows *what*.

### When to write memories
After these events, write or correct memories immediately — don't defer to session end:
- **Fixed a bug** → write/correct the relevant `fact` about how the system works
- **Changed architecture or configuration** → correct stale `decision`/`fact`, write new ones
- **Established a workflow** (deploy, test, debug sequence) → write a `procedure`
- **Discovered something non-obvious** about the codebase → write a `fact`
- **Made a design choice** between alternatives → write a `decision` with rationale

Use `memspec add <type> "<title>" --body "<content>" --source <agent> --tags <tags>`.
Use `memspec correct <id> --reason "<why>" --replace "<new content>"` for stale memories.

### Guidelines
- Only write knowledge that helps a future agent starting cold. No session transcripts.
- If the store is thin, persist stable facts and decisions you discover while scanning the repo.
- If you discover memory drift, correct the stale memory — don't leave both versions active.
- Never store secrets in memory files.
- When classifying, ask: does a future agent need this to understand *why* (decision), to *do something* (procedure), or to know *what's true* (fact)?
<!-- memspec:init:end -->
