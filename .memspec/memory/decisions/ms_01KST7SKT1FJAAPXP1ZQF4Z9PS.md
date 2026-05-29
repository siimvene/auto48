---
id: ms_01KST7SKT1FJAAPXP1ZQF4Z9PS
type: decision
state: active
confidence: 0.7
created: '2026-05-29T16:06:37.120Z'
source: claude
tags:
  - architecture
  - stack
  - layout
decay_after: '2026-11-25T16:06:37.122Z'
---
# Stack and layout: FastAPI backend + Nuxt 4/Vue 3 frontend

auto48 is an auto24.ee competitor (Estonian car marketplace). Backend: FastAPI + async SQLAlchemy 2.0 in src/auto48 (root src/ layout, not backend/), settings via get_settings() pydantic-settings factory (env AUTO48_*), DbSession Annotated DI. Frontend: Nuxt 4/Vue 3 in frontend/, talks to backend over HTTP/JSON only. Dev DB defaults to sqlite; prod uses postgresql+asyncpg via Alembic. Coding standards adopted from shared development standards (.cursor/rules), scrubbed of internal hosts/tokens since this is a public repo. Why: keeps rule path references (src/<pkg>, docs/) consistent with the .mdc rules.
