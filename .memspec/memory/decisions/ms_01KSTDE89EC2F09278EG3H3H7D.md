---
id: ms_01KSTDE89EC2F09278EG3H3H7D
type: decision
state: active
confidence: 0.7
created: '2026-05-29T17:45:16.332Z'
source: claude
tags:
  - product
  - scope
  - parked
  - trust
  - x-tee
  - vehicle-data
decay_after: '2026-11-25T17:45:16.340Z'
---
# Parked: registry-verified vehicle tag + direct X-tee adapter

Decision (2026-05-29): park the 'registry-verified' vehicle-data tag AND the direct Transpordiamet/X-tee adapter. Rationale: Estonia exposes no plain registry REST API — X-tee is the only official programmatic route and needs RIA membership + an X-Road security server + a per-registry data-sharing agreement (months, may be refused). The commercial adapter (carVertical/autoDNA) behind VehicleDataPort already covers v1 (VIN decode + spec + history timeline). We keep vehicle-data auto-fill + history timeline; we drop the 'verified' positioning/badge for vehicle data. NOT affected: the separate eID verified-SELLER badge (still planned Phase 2). Revisit X-tee only if an authoritative guarantee or better per-lookup cost-at-scale justifies onboarding — it's an adapter swap, not a rewrite. Tracked under Parked/backlog in docs/implementation-plan.md.
