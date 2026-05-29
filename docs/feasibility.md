# auto48 — External Dependency Feasibility

What external data/integrations a startup can realistically obtain, and how fast. This is what
makes **trust-included v1** achievable without waiting on state bureaucracy. The driving
distinction is **weeks vs months** — it sets what lands in Phase 1 vs later.

## Summary

| Area | Verdict | v1 approach |
|---|---|---|
| Vehicle data — commercial (carVertical/autoDNA) | ✅ ~1–2 weeks | **v1 source** for VIN decode + spec + history |
| Vehicle data — Transpordiamet via X-tee | ⛔ months (may be refused) | Later premium adapter behind same port |
| eID (TARA / Smart-ID / Mobile-ID) | ✅ 3–6 weeks | Stub v1; start RIA application week 1 |
| Payments (Stripe Connect / Montonio) | ✅ 1–2 weeks | Phase 1b |
| Valuation data (Autovista / OBV) | ✅ weeks (optional) | v0 = own-listing comparables |

## 1. Estonian vehicle registry data (Transpordiamet / Liiklusregister)

Official specs, ownership/registration history, inspection (ülevaatus) records, and odometer
readings *at inspection points* exist — but access is gated:

- **X-tee / X-Road membership** requires a formal **RIA contract** plus a **separate data-sharing
  agreement with Transpordiamet**. No public self-service API; no confirmed reseller for raw data.
- Realistic setup: **4–8 weeks minimum, possibly months**, and may face negotiation friction or refusal.

→ **Skip for v1.** Treat direct X-tee as a later premium source behind `VehicleDataPort`.

## 2. VIN decoding & vehicle-history providers (the v1 workaround)

Commercial APIs aggregate official inspection/registry data across the EU (incl. Estonia) with
**no regulatory barrier** — standard B2B contract + REST API:

- **carVertical** — VIN decode + history (mileage, ownership, accident, theft), API for business.
- **autoDNA** — vehicle history across 26+ EU countries from 50k+ sources.
- Pricing: ~€25–39 per consumer report; bulk/API by quote (budget ~€500–2k/mo at volume).
- Onboarding: **~1–2 weeks**.

→ **v1 `VehicleDataPort` adapter.** Cache per VIN; fetch on listing **create**, not per view, to control cost.

## 3. Estonian eID — TARA / Smart-ID / Mobile-ID

State **TARA** gateway federates Smart-ID, Mobile-ID, ID-card via **OpenID Connect**; nationwide adoption.

- Requires registering the service with **RIA** (digitally signed application). No direct licensing cost.
- Timeline: test ~1–2 weeks, production approval ~2–4 weeks → **~3–6 weeks total**.

→ **Stub `EidPort` in v1; start the RIA application in week 1**; ship the verified-seller badge when live (Phase 2).

## 4. Payments — dealer subscriptions + (later) escrow

| Provider | Marketplace | Subscriptions | Escrow / hold | Onboarding |
|---|---|---|---|---|
| **Stripe Connect** | ✅ split payouts | ✅ full billing | ✅ delayed payout | 1–2 weeks |
| **Montonio** | ✅ (local card/bank) | ⚠️ limited | ❌ | 1–2 weeks |

→ **Stripe Connect** primary (subs + promotions now, escrow in Phase 5); **Montonio** as cheaper local option.

## 5. Valuation data

- **DIY v0**: median/regression over our own comparable listings — only dev time. Good enough to start.
- **Commercial** (Autovista, Orange Book Value): benchmarks/residual values by quote (~weeks to integrate) — optional later.
- ⛔ **Not an option:** scraping auto24/ss.lv/autoplius for prices. Clean-room rule — see product scope anti-goals.

## Sources

Transpordiamet vehicle registration; RIA X-tee overview + eID integration tools; TARA technical spec;
carVertical API; autoDNA; Stripe Connect / Billing (Estonia); Montonio pricing; Autovista API; Orange Book Value (EE).
