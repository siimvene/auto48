---
id: ms_01KST8ZYG761MX86W3RTNX4FC8
type: decision
state: active
confidence: 0.7
created: '2026-05-29T16:27:33.254Z'
source: claude
tags:
  - product
  - scope
  - v1
  - sequencing
  - feasibility
decay_after: '2026-11-25T16:27:33.256Z'
---
# v1 scoping locked: both-supply, trust-included, EE-first, dealer subs+promotions

Product-owner decisions for auto48 v1: (1) cold-start = BOTH supply sides in parallel (dealer feeds via FeedPort + free private listings); (2) trust-included v1 = vehicle-data auto-fill + history timeline (mileage-rollback flag) ship in Phase 1, not deferred; (3) Estonia-first (Baltic LV/LT = Phase 7); (4) monetization = dealer subscriptions + paid promotions (free private listings), via PaymentPort. Feasibility-driven sequencing: VehicleDataPort v1 adapter = COMMERCIAL history API (carVertical/autoDNA, ~1-2wk) NOT direct Transpordiamet/X-tee (months of RIA+X-tee bureaucracy, deferred to later premium adapter). eID (TARA/Smart-ID) ~3-6wk RIA approval -> stub in v1, start application week 1, go live Phase 2. Payments: Stripe Connect (subs/escrow) + Montonio (local), ~1-2wk, Phase 1b. Valuation v0 = own-listing comparables only. HARD: never scrape auto24/ss.lv/autoplius for prices (clean-room). Phase 1 split into 1a (core+trust hook) and 1b (both-supply+monetization). See docs/feasibility.md, docs/implementation-plan.md. Supersedes the earlier high-level scope decision.
