# auto48 — Architecture

Layered/hexagonal: thin HTTP layer → services (domain logic) → data access, with **ports
& adapters** for every external system so the core stays clean-room and providers are
swappable. Stateless services; long work runs in background workers (per component standards).

## System overview

```
                  ┌─────────────────────────────────────────────┐
   Browser/PWA →  │  Nuxt 4 / Vue 3 frontend (HTTP/JSON only)     │
                  └───────────────────────┬─────────────────────┘
                                          │  REST /v1 (OpenAPI, RFC 7807)
                  ┌───────────────────────▼─────────────────────┐
                  │  FastAPI app (src/auto48)                     │
                  │   routers → services → repositories           │
                  │   ports: registry, eid, valuation, payment,   │
                  │          insurance, feed, media, notify       │
                  └───┬───────────┬───────────┬──────────┬───────┘
                      │           │           │          │
                  ┌───▼───┐  ┌────▼────┐  ┌───▼───┐  ┌───▼────────┐
                  │Postgres│  │ Redis   │  │Object │  │Search engine│
                  │+PostGIS│  │ +queue  │  │store  │  │(FTS→Typesense)
                  └────────┘  └────┬────┘  └───────┘  └────────────┘
                                   │
                        ┌──────────▼───────────┐
                        │ Workers (arq/async)   │
                        │ feed ingest · alerts  │
                        │ valuation · images    │
                        └───────────────────────┘
```

## Tech choices

| Concern | MVP | Later | Why |
|---|---|---|---|
| API | FastAPI (async) | — | Already scaffolded; async I/O |
| DB | Postgres + **PostGIS** | read replicas | Geo/map search, JSONB specs |
| Search | Postgres FTS + facets | **Typesense/Meilisearch** | Typo-tolerant, instant facets |
| Cache/queue | Redis | — | Sessions, rate limit, job broker |
| Workers | **arq** (async + Redis) | — | Ingest, alerts, valuation, images off the request path |
| Object storage | S3-compatible (**MinIO** local) | CDN | Photos; never on local FS (stateless) |
| Frontend | Nuxt 4 / Vue 3 (SSR/PWA) | — | SEO for listings + app feel |
| Auth | OAuth2/OIDC + email | **eID (TARA/Smart-ID)** | Estonian identity = trust badge |
| Payments | adapter only | **Montonio**/Stripe | Promotions, deposit/escrow |
| Observability | structlog JSON + OTel | dashboards | Correlation IDs, traces |

## Ports (interfaces) — keep the core clean-room

Each is a Python `Protocol`/ABC in `src/auto48/ports/`, with a `stub` adapter for dev and
a real adapter wired by config. The domain never imports a vendor SDK directly.

| Port | Responsibility | Real adapter (planned) |
|---|---|---|
| `RegistryPort` | Vehicle data + history by plate/VIN | Transpordiamet via X-tee (X-Road) |
| `EidPort` | Identity verification + e-signature | TARA / Smart-ID / Mobile-ID |
| `ValuationPort` | Price estimate + deal score | v0 comparables → ML model / data partner |
| `PaymentPort` | Promotions, deposits, escrow | Montonio / Stripe |
| `InsurancePort` | Insurance & financing quotes | Broker/bank partners |
| `FeedPort` | Ingest dealer inventory feeds | XML/CSV/JSON feed parsers |
| `MediaPort` | Store + process images | MinIO/S3 + Pillow pipeline |
| `NotifyPort` | Email/push (alerts, messages) | SMTP/SES + Web Push |

## Domain model (core entities)

```
User ──< SellerProfile (PRIVATE | DEALER)            verified: bool (eID)
SellerProfile ──< Listing >── Vehicle                 Listing.status: draft|active|sold|expired
Vehicle ── make/model/variant, specs(JSONB), fuel, body, transmission, drivetrain
Vehicle ──< VehicleHistoryEvent (registration|odometer|inspection|owner_change|damage|import)
Listing ──< Photo (ordered)                           Photo.processed: bool
Listing ── Valuation (estimate, deal_score, ts)
Listing ── geo: Point (PostGIS)  ── price_eur, mileage_km, year, location
User ──< SavedSearch ──< Alert (match → NotifyPort)   SavedSearch.query: facet JSON
Conversation (buyer, seller, listing) ──< Message
Dealer ──< DealerFeed (url, format, schedule) ──< IngestRun (stats, errors)
Listing ──< Lead (source, contact_at)                 dealer analytics
Listing ──< Promotion (type, period) ── PaymentPort
Transaction (listing, buyer, seller) ── deposit, Contract (e-signed via EidPort), transfer
```

### Key invariants
- A `Listing` references exactly one `Vehicle`; registry-verified fields are read-only.
- `VehicleHistoryEvent`s are append-only and ordered by `occurred_at` → the trust timeline;
  a decreasing odometer raises a **rollback flag**.
- Search index is derived state, rebuilt from Postgres (Postgres is the source of truth).
- All money in integer **cents EUR**; all times timezone-aware UTC.

## API surface (v1, indicative)

```
GET    /v1/listings            search + facets + pagination
POST   /v1/listings            create (draft)
GET    /v1/listings/{id}       detail (+ valuation, history timeline)
PATCH  /v1/listings/{id}
POST   /v1/listings/{id}/photos
GET    /v1/vehicles/lookup?plate=… | ?vin=…   registry auto-fill (RegistryPort)
GET    /v1/valuations?…        estimate + deal score (ValuationPort)
POST   /v1/saved-searches      + GET/DELETE          alerts on match
POST   /v1/conversations/{id}/messages
POST   /v1/dealer/feeds        register feed → background ingest
POST   /v1/auth/eid/start      eID verification (EidPort)   [Phase 2]
```

## Cross-cutting

- **Security**: input validation, OAuth2/OIDC bearer, no PII/tokens in logs, rate limiting,
  plate/face blur in photos, GDPR data-subject endpoints. See `.cursor/rules/common/security.mdc`.
- **Migrations**: Alembic as a deploy step (never on startup).
- **Config**: env only (`AUTO48_*`) via `get_settings()`.
- **Testing**: pytest + pytest-asyncio; integration tests for each port adapter against its stub.
