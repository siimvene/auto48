# auto48 — Implementation Plan

Single source of truth for project status and roadmap
(per `.cursor/rules/ai-tools/project-context.mdc`). Update after each milestone.

## Vision

The most **trustworthy** and **intelligent** way to buy/sell a car in the Baltics — Estonia-first,
Baltic-ready. See [`product-scope.md`](product-scope.md) for the full product and the six "10x"
pillars; [`architecture.md`](architecture.md) for system design and the domain model.
Clean-room build: external data only via official/consented adapters (registry, eID, feeds).

## Status

**Phase 0 — Scaffold (done)**

- [x] Repository seeded with shared development standards (`.cursor/rules`, skills, hooks)
- [x] memspec memory store initialised
- [x] FastAPI backend skeleton: settings, async DB, health, example `listings` resource
- [x] Alembic async migration environment
- [x] Nuxt 4 / Vue 3 frontend skeleton
- [x] Product scope + architecture documented

**Phase 1 — Core marketplace (next)** — see scope "MVP cut".

## Roadmap (phased)

| # | Phase | Delivers | Key pieces |
|---|---|---|---|
| 0 | Scaffold | Repo, standards, skeletons | ✅ done |
| 1 | **Core marketplace** | Find a car ↔ list in <60s | Listings CRUD+photos, facet search (Postgres FTS), accounts (email/OAuth, eID interface), messaging, dealer feed (1 format), valuation v0, **CI + first migration** |
| 2 | **Trust layer** | Registry-verified data + history | `RegistryPort` (Transpordiamet/X-tee), history timeline + rollback flag, `EidPort` (Smart-ID/Mobile-ID) verified badge, fraud signals |
| 3 | **Price intelligence** | Deal score + TCO | Valuation model, deal-score badge, TCO calc, financing/insurance quotes (`InsurancePort`) |
| 4 | **Discovery** | Find *the* car | Typesense/Meilisearch, saved-search real-time alerts, map + NL search, recommendations |
| 5 | **Transactions** | Buy safely, end-to-end | Test-drive scheduling, deposit/escrow (`PaymentPort`), e-signed contract (`EidPort`), ownership transfer |
| 6 | **Dealer suite** | Pro tooling + revenue | Multi-format feeds, lead CRM, analytics, promotions/payments |
| 7 | **Baltic + EV + PWA** | Scale & polish | EE/LV/LT, ET/EN/RU/LV/LT i18n, import calculator, EV fields, PWA/a11y/perf |

### Phase 1 task seeds
- [ ] CI pipeline (ruff + mypy + pytest) on push/PR
- [ ] Real `Vehicle`/`Listing`/`SellerProfile`/`Photo` models + first Alembic migration (replace dev `create_all`)
- [ ] Faceted search endpoint (Postgres FTS) + listing detail
- [ ] Accounts + auth (OAuth2/OIDC; `EidPort` interface stubbed)
- [ ] Photo upload via `MediaPort` (MinIO) + processing worker (arq)
- [ ] `ValuationPort` v0 (comparables) + buyer↔seller messaging
- [ ] `FeedPort` + one dealer feed format ingested by a worker
- [ ] Frontend: browse/search/detail/create flows

> Update this file (don't assume prerequisites) before planning new work.
