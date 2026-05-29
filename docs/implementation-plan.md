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

**Phase 1a — Core marketplace + trust hook (complete)** — backend: 6 routers (health, auth,
listings/search, vehicles+history, photos, conversations), mypy `--strict` clean, 57 tests passing;
frontend: browse/detail/sell built against the real contract (`nuxt build` green). External/deferred:
RIA/TARA eID application; local `create_all`→Alembic. **Next: Phase 1b.**

## Roadmap (phased)

| # | Phase | Delivers | Key pieces |
|---|---|---|---|
| 0 | Scaffold | Repo, standards, skeletons | ✅ done |
| 1a | **Core + trust hook** | Find a trusted car ↔ list in <60s | Domain models + first migration, facet search (Postgres FTS), **`VehicleDataPort` auto-fill + history timeline (commercial adapter)**, accounts (email/OAuth, `EidPort` stub), photos (`MediaPort`/MinIO + worker), messaging, **CI** |
| 1b | **Both-supply + monetization** | Dealer inventory + revenue | Dealer accounts + `FeedPort` (1 format) + ingest worker, `PaymentPort` (Stripe Connect: subs + promotions), `ValuationPort` v0 (own comparables) + deal-score, saved search + email alert |
| 2 | **Trust depth** | Verified sellers + fraud signals | `EidPort` go-live (seller verified badge), fraud signals (stolen/duplicate/scam). *Registry/X-tee vehicle verification → parked (backlog).* |
| 3 | **Price intelligence** | Deal score + TCO | Valuation model, TCO calc, financing/insurance quotes (`InsurancePort`) |
| 4 | **Discovery** | Find *the* car | Typesense/Meilisearch, saved-search real-time alerts, map + NL search, recommendations |
| 5 | **Transactions** | Buy safely, end-to-end | Test-drive scheduling, deposit/escrow (`PaymentPort`), e-signed contract (`EidPort`), ownership transfer |
| 6 | **Dealer suite** | Pro tooling + revenue | Multi-format feeds, lead CRM, analytics, richer promotions |
| 7 | **Baltic + EV + PWA** | Scale & polish | EE→LV/LT, ET/EN/RU/LV/LT i18n, import calculator, EV fields, PWA/a11y/perf |

### Phase 1a task seeds
- [x] CI pipeline (ruff + mypy + pytest) on push/PR
- [x] Real `Vehicle`/`Listing`/`SellerProfile`/`Photo`/`VehicleHistoryEvent` models + first Alembic migration
- [x] Faceted search endpoint (ILIKE; Postgres FTS in Phase 4) + listing detail
- [x] `VehicleDataPort`: stub + commercial adapter skeleton; plate/VIN auto-fill + history timeline (rollback flag)
- [x] Accounts + auth (JWT bearer; `EidPort` interface stubbed) — **TODO: start RIA/TARA application**
- [x] Photo upload via `MediaPort` (Stub/S3) + processing worker (arq), graceful Redis-down
- [x] Buyer↔seller messaging
- [x] Frontend: browse/search/detail/create flows (scaffolded)
- [x] Reconcile frontend types/pages to backend's **nested-vehicle** response shape — verified with `nuxt build` (✨ Build complete); also fixed sell-form enum values (plugin_hybrid/wagon/semi_automatic/cvt)
- [x] Wire auth (`CurrentUser`) into photos (ownership-checked) and messaging (buyer/sender from token); mypy `--strict` clean; full suite 57 passing
- [ ] Replace local `create_all` with `alembic upgrade head` — **deferred by decision**: `create_all` is gated to `environment == "local"` (dev/test convenience only); production already uses Alembic. Revisit if local/prod parity is needed.

### Phase 1b task seeds — complete (backend)
- [x] Dealer accounts + `FeedPort` (CSV/JSON) + ingest worker + `/v1/dealer/feeds` (dealer-only, VIN upsert, IngestRun tracking)
- [x] `PaymentPort` (Stripe adapter + stub): dealer subscriptions + listing promotions (`/v1/billing/*`, ownership-checked)
- [x] `ValuationPort` v0 (own-listing comparables, median + p25/p75 band) + deal-score (`/v1/valuations`)
- [x] Saved search + email alert (`NotifyPort` SMTP/stub) + alerts worker (`/v1/saved-searches`)
- [x] Single Alembic migration for the 6 new tables; full suite 97 passing, mypy `--strict` clean, 28 routes
- [ ] Frontend surfaces for 1b (dealer feed mgmt, deal-score badge wired to `/v1/valuations`, saved-search UI) — next frontend pass

## Delivered cross-phase (via subagents, ahead of sequence)

Backend slices implemented against the spec pillars (no external deps; auth-gated where noted):
- **Fraud signals** (Phase 2 trust): duplicate-listing detection + underpriced-vs-market +
  scam-text scoring → `GET /v1/listings/{id}/risk` (risk score/level/flags). `services/fraud.py`.
- **TCO + financing + insurance** (Phase 3): `InsurancePort` (+ stub), `services/tco.py` →
  `GET /v1/listings/{id}/tco`, `GET /v1/listings/{id}/financing`.
- **Test-drive scheduling** (Phase 5 transactions): `TestDriveBooking` model + auth-gated
  request/confirm/decline/cancel under `/v1/listings/{id}/test-drives` and `/v1/test-drives/*`.
- **Recommendations / similar** (Phase 4 discovery): `GET /v1/listings/{id}/similar`,
  `GET /v1/recommendations`. `services/recommendations.py`.
- **Escrow / deposit** (Phase 5 transactions): `Deposit` model + `PaymentPort` hold/release/refund
  → `POST /v1/listings/{id}/deposit`, `/v1/deposits/{id}/release|refund`.
- **Import-cost calculator** (Phase 7): EE landed-cost (customs/VAT/2025 car tax/transport) →
  `GET|POST /v1/import-calculator`.
- **Dealer analytics** (Phase 6): inventory/leads/test-drives/feed-health aggregates →
  `GET /v1/dealer/analytics`.
- **Map / radius search** (Phase 4): haversine `GET /v1/listings/nearby?lat=&lon=&radius_km=`.
- **Natural-language search** (Phase 4): rule-based ET/EN parser → `GET /v1/search?q=...`.
- **Stolen-vehicle check** (Phase 2 trust): `StolenVehiclePort` (+stub) → `GET /v1/vehicles/{vin}/stolen-check`.

48 API routes, 272 tests, mypy `--strict` clean, 4 migrations.

Still open — NOT implementable without external access / running infra / frontend work:
eID go-live + X-tee registry (external/parked), search-engine swap to Typesense/Meilisearch +
real-time push alerts (infra), e-signed contract (eID-gated), i18n / EV structured fields / PWA,
and the matching **frontend surfaces** for the new endpoints (frontend is under active redesign).

## Parked / backlog

- **Registry-verified vehicle data ("verified" tag) + direct Transpordiamet/X-tee adapter.**
  Parked 2026-05-29. Reason: X-tee is the only official programmatic route (no plain registry
  REST API); it needs RIA membership + an X-Road security server + a per-registry agreement
  (months, may be refused), and the commercial adapter (carVertical/autoDNA) already covers v1.
  Revisit if/when we need an authoritative "registry-verified" guarantee or better per-lookup
  cost at scale. The `VehicleDataPort` abstraction means this is an adapter swap, not a rewrite.

> Update this file (don't assume prerequisites) before planning new work.
