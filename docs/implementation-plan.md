# auto48 — Implementation Plan

Single source of truth for project status and roadmap
(per `.cursor/rules/ai-tools/project-context.mdc`). Update after each milestone.

## Vision

The most **trustworthy** and **intelligent** way to buy/sell a car in the Baltics — Estonia-first,
Baltic-ready. See [`product-scope.md`](product-scope.md) for the full product and the six "10x"
pillars; [`architecture.md`](architecture.md) for system design and the domain model.
Clean-room build: external data only via official/consented adapters (vehicle-data provider, eID, feeds).
Locked decisions: **both-supply** (dealer feeds + free private listings), **trust-included v1**,
**Estonia-first**, **dealer subs + promotions**. Feasibility: [`feasibility.md`](feasibility.md).

## Status

**Phase 0 — Scaffold (done)**

- [x] Repository seeded with shared development standards (`.cursor/rules`, skills, hooks)
- [x] memspec memory store initialised
- [x] FastAPI backend skeleton: settings, async DB, health, example `listings` resource
- [x] Alembic async migration environment
- [x] Nuxt 4 / Vue 3 frontend skeleton
- [x] Product scope + architecture documented

**Phase 1a — Core marketplace + trust hook (next)** — see scope "MVP cut".

## Roadmap (phased)

| # | Phase | Delivers | Key pieces |
|---|---|---|---|
| 0 | Scaffold | Repo, standards, skeletons | ✅ done |
| 1a | **Core + trust hook** | Find a trusted car ↔ list in <60s | Domain models + first migration, facet search (Postgres FTS), **`VehicleDataPort` auto-fill + history timeline (commercial adapter)**, accounts (email/OAuth, `EidPort` stub), photos (`MediaPort`/MinIO + worker), messaging, **CI** |
| 1b | **Both-supply + monetization** | Dealer inventory + revenue | Dealer accounts + `FeedPort` (1 format) + ingest worker, `PaymentPort` (Stripe Connect: subs + promotions), `ValuationPort` v0 (own comparables) + deal-score, saved search + email alert |
| 2 | **Trust depth** | Verified sellers + official data | `EidPort` go-live (verified badge), Transpordiamet/X-tee adapter, fraud signals (stolen/duplicate/scam) |
| 3 | **Price intelligence** | Deal score + TCO | Valuation model, TCO calc, financing/insurance quotes (`InsurancePort`) |
| 4 | **Discovery** | Find *the* car | Typesense/Meilisearch, saved-search real-time alerts, map + NL search, recommendations |
| 5 | **Transactions** | Buy safely, end-to-end | Test-drive scheduling, deposit/escrow (`PaymentPort`), e-signed contract (`EidPort`), ownership transfer |
| 6 | **Dealer suite** | Pro tooling + revenue | Multi-format feeds, lead CRM, analytics, richer promotions |
| 7 | **Baltic + EV + PWA** | Scale & polish | EE→LV/LT, ET/EN/RU/LV/LT i18n, import calculator, EV fields, PWA/a11y/perf |

### Phase 1a task seeds
- [ ] CI pipeline (ruff + mypy + pytest) on push/PR
- [ ] Real `Vehicle`/`Listing`/`SellerProfile`/`Photo`/`VehicleHistoryEvent` models + first Alembic migration (replace dev `create_all`)
- [ ] Faceted search endpoint (Postgres FTS) + listing detail
- [ ] `VehicleDataPort`: stub + commercial adapter; plate/VIN auto-fill + history timeline (rollback flag)
- [ ] Accounts + auth (OAuth2/OIDC; `EidPort` interface stubbed); **start RIA/TARA application**
- [ ] Photo upload via `MediaPort` (MinIO) + processing worker (arq)
- [ ] Buyer↔seller messaging
- [x] Frontend: browse/search/detail/create flows (scaffolded)
- [ ] Reconcile frontend types/pages to backend's **nested-vehicle** response shape (`vehicle.make`, `price_eur_cents`, `location_county`) — verify end-to-end with `npm install` + live API

### Phase 1b task seeds
- [ ] Dealer accounts + `FeedPort` + one dealer feed format ingested by a worker
- [ ] `PaymentPort` (Stripe Connect): dealer subscriptions + paid promotions
- [ ] `ValuationPort` v0 (own-listing comparables) + deal-score badge
- [ ] Saved search + basic email alert (`NotifyPort`)

> Update this file (don't assume prerequisites) before planning new work.
