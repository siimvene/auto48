# auto48 — Product Scope

> Vision: the most **trustworthy** and **intelligent** way to buy and sell a car in the
> Baltics. Estonia-first, Baltic-ready. Clean-room build — all external data enters through
> official, consented adapters (vehicle registry, eID, dealer feeds), never by scraping.

## Who it's for

| Segment | Need |
|---|---|
| **Private buyer** | Find the right car fast, trust the data, know it's a fair price, buy safely |
| **Private seller** | List in 60 seconds, reach buyers, avoid scams and tyre-kickers |
| **Dealer / pro** | Push inventory via feed, manage leads, measure performance, promote stock |
| **Importer** | Compare cross-border, understand true landed cost (tax, transport, conversion) |

## Where the incumbent (auto24.ee) leaves room — our wedge

These are general classifieds pain points, not reverse-engineered internals:

1. **Trust is manual.** Buyers cross-check mileage, history and damage themselves on
   external sites. Sellers aren't identity-verified. Scams persist.
2. **No price intelligence.** No fair-price signal, no valuation, no total-cost-of-ownership.
3. **Search is basic.** Weak facets, no typo tolerance, weak/late saved-search alerts.
4. **Listing is friction + pay-to-list** for private sellers; no auto-fill from the plate.
5. **No transaction layer.** Contract, deposit, ownership transfer all happen off-platform.
6. **Ad-heavy, dated, weak mobile.** No EV-specific data despite a fast-growing EV market.

## The "10x" — six product pillars

### 1. Trust by default
- **Registry-verified vehicle data**: auto-fill make/model/spec/first-registration from the
  plate or VIN via the Estonian Transport Administration (Transpordiamet) adapter.
- **History timeline**: ownership count, odometer readings over time (**mileage-rollback
  flag**), inspection (ülevaatus) history, import origin, write-off/damage markers.
- **eID-verified sellers**: Smart-ID / Mobile-ID / ID-card verification → "verified" badge.
- **Fraud signals**: stolen-vehicle check, duplicate-listing detection, scam-pattern scoring.

### 2. Price intelligence
- **Instant valuation** and a **deal score** ("good deal / fair / overpriced") on every listing.
- **Total cost of ownership**: tax, insurance estimate, fuel/charging, maintenance, depreciation.
- **Financing & insurance quotes** inline (partner adapters), with monthly-payment view.

### 3. Search that finds *the* car
- Typo-tolerant, faceted, instant search; **map-based** and **natural-language** queries.
- **Saved searches with real-time alerts** (push + email) — first to know on a new match.
- "Similar cars" and personalised recommendations.

### 4. Frictionless listing
- **Plate/VIN auto-fill** → most fields pre-populated from the registry.
- **AI photo cleanup** (background, crop, plate blur) and **AI-drafted description**.
- **Free private listings**; revenue from promotions and dealer/pro tooling.

### 5. End-to-end transactions
- In-app **messaging**, **test-drive scheduling**, **secure deposit/escrow**.
- **Digital purchase–sale contract** e-signed via Smart-ID/Mobile-ID.
- **Ownership-transfer** guidance/handoff to the registry.

### 6. EV-ready, Baltic-wide, fast
- EV fields: battery health, real range, charging standards, charging-cost calculator.
- **EE/LV/LT** listings, multilingual (ET/EN/RU/LV/LT), **import-cost calculator**.
- Mobile-first **PWA**, minimal ads, accessible (WCAG), fast.

## Locked decisions

| Decision | Choice | Why it matters |
|---|---|---|
| **Cold-start supply** | **Both in parallel** — dealer feeds + free private listings | Feeds give instant inventory; free private listings are the wedge vs pay-to-list |
| **MVP differentiation** | **Trust-included v1** — vehicle-data auto-fill + history timeline in v1 | Ships the actual wedge at launch, not a thin clone |
| **Geography** | **Estonia-first** | Baltic (LV/LT) is Phase 7 |
| **Monetization** | **Dealer subscriptions + promotions** | Free private listings stay free; revenue from pros + paid bumps |

Trust data is sourced from a **commercial history adapter (carVertical/autoDNA)** in v1
(obtainable in ~1–2 weeks); direct Transpordiamet/X-tee access is a later, premium track
(months of bureaucracy). See [`feasibility.md`](feasibility.md).

## MVP cut — trust-included marketplace loop

A buyer can **find** a car, **trust its history**, and **contact** a seller; a seller can **list**
in under a minute with most fields auto-filled. Phase 1 is split into two shippable increments:

**Phase 1a — core + trust hook**
- Listings: create/edit/search/detail, photos, core facets (make, model, year, price, mileage, fuel, body, transmission, location).
- **Vehicle-data auto-fill + history timeline** (mileage-rollback flag) via `VehicleDataPort` — the v1 differentiator.
- Accounts: email/OAuth now; **`EidPort` stubbed**, RIA/TARA application started in parallel.
- Search: Postgres full-text + facets (swap to a dedicated engine in Phase 4).
- Photos via `MediaPort` (MinIO) + background image worker; buyer ↔ seller messaging.

**Phase 1b — both-supply + monetization**
- Dealer accounts + **one feed format** ingested by a background worker (`FeedPort`).
- **Dealer subscriptions + paid promotions** via `PaymentPort` (Stripe Connect; Montonio local).
- Rules-based valuation **v0** (median of own comparable listings) behind `ValuationPort` + deal-score badge.
- Saved search + basic email alert.

Everything beyond MVP is sequenced in [`implementation-plan.md`](implementation-plan.md).

## What we will NOT do

- No scraping or reverse-engineering of competitors. External data only via official/consented
  adapters (registry, eID, dealer feeds, licensed reference data).
- **Valuation and price benchmarks come from our own listings + licensed history data only** —
  never from scraping auto24/ss.lv/autoplius or any competitor.
- No storing third-party personal data without a lawful basis (GDPR).
- No dark patterns, no ad clutter, no pay-to-list walls for private sellers.

## How we measure "10x"

- **Time-to-list** (target < 60s) · **time-to-first-lead** · **alert latency** (target < 60s).
- **Trust coverage**: % listings with registry-verified data and a history timeline.
- **Search success**: % sessions ending in a contact/save · zero-result rate.
- **Valuation coverage & accuracy** · **buyer trust (CSAT)** · **fraud-report rate**.
