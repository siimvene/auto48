# auto48 — Implementation Plan

Single source of truth for project status and roadmap
(per `.cursor/rules/ai-tools/project-context.mdc`). Update after each milestone.

## Vision

An open car marketplace for the Estonian/Baltic market — an [auto24.ee](https://www.auto24.ee)
competitor. FastAPI backend, Nuxt 4 / Vue 3 frontend.

## Status

**Phase 0 — Scaffold (in progress)**

- [x] Repository seeded with shared development standards (`.cursor/rules`, skills, hooks)
- [x] memspec memory store initialised
- [x] FastAPI backend skeleton: settings, async DB, health, example `listings` resource
- [x] Alembic async migration environment
- [x] Nuxt 4 / Vue 3 frontend skeleton
- [ ] CI (lint + test) pipeline
- [ ] First real migration committed (replace dev `create_all`)
- [ ] Authentication (OAuth 2.1 / OIDC per integration standards)

## Roadmap (high level)

1. **Listings domain** — search, filters, pagination, photos
2. **Sellers & accounts** — auth, dealer vs private listings
3. **Search & discovery** — full-text + faceted filters
4. **Frontend** — listing browse/detail, search UX
5. **Ingestion** — import/scrape pipelines for inventory

> Update this file (don't assume prerequisites) before planning new work.
