---
id: ms_01KST89QYVC12Y0B8ECQNY0G4S
type: decision
state: active
confidence: 0.7
created: '2026-05-29T16:15:25.659Z'
source: claude
tags:
  - product
  - scope
  - architecture
  - differentiators
decay_after: '2026-11-25T16:15:25.660Z'
---
# Product scope: trust + price intelligence as the 10x wedge; clean-room only

auto48 competes with auto24.ee on six pillars: (1) trust by default (registry-verified data via Transpordiamet/X-tee, history timeline with mileage-rollback flag, eID-verified sellers), (2) price intelligence (instant valuation, deal score, TCO, financing/insurance quotes), (3) typo-tolerant faceted search + real-time saved-search alerts, (4) frictionless listing (plate/VIN auto-fill, AI photos/desc, free private listings), (5) end-to-end transactions (escrow, e-signed contract via Smart-ID, ownership transfer), (6) EV-ready + Baltic-wide + PWA. HARD CONSTRAINT: clean-room — no scraping/reverse-engineering of competitors; all external data via official/consented adapters (RegistryPort, EidPort, FeedPort, etc.) as ports/adapters with stub impls. Architecture: hexagonal, Postgres+PostGIS, Redis+arq workers, S3/MinIO media, Postgres FTS->Typesense. See docs/product-scope.md + docs/architecture.md. MVP=Phase 1 core marketplace loop.
