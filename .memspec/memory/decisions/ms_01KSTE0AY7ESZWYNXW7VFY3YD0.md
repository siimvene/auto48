---
id: ms_01KSTE0AY7ESZWYNXW7VFY3YD0
type: decision
state: active
confidence: 0.7
created: '2026-05-29T17:55:08.870Z'
source: claude-opus (frontend design incorporation task)
tags:
  - frontend
  - design
  - nuxt
  - vue
  - signal
  - ui
  - valuation
decay_after: '2026-11-25T17:55:08.873Z'
---
# Frontend adopts "Signal" (Direction B) design system

The Nuxt frontend was restyled from the placeholder blue theme to the "Signal" design (Direction B from the design package: dark dramatic hero + electric volt-lime accent #C2EE45, Space Grotesk / Hanken Grotesk / JetBrains Mono fonts, Estonian copy). The other option (Direction A "Studio", editorial cream/serif) was not used; user picked B.

Key implementation facts for future agents:
- Global design system lives in frontend/app/assets/css/signal.css (tokens at :root, component classes app-wide — NOT scoped under .signal). Registered via nuxt.config css[] + Google Fonts <link> in app.head.
- Icons: @iconify/vue + bundled @iconify-json/lucide collection registered offline in app/plugins/iconify.ts (addCollection) so icons render SSR/offline; use <Icon name="car-front" :size="18" /> wrapper (app/components/Icon.vue), names are lucide icon names.
- Pages: index.vue = dark marketing landing (hero + AI command bar → /search?q=, category rail → /search?body=<enum>, recommended grid, feature cards). search.vue = results (LightNav + query banner + filter sidebar + sort + grid + pagination). listings/[id].vue = detail (gallery, specs grid, trust placeholder, sticky buybox with REAL fairness, similar). sell.vue = restyled form (Estonian).
- Shared components: LightNav.vue, DarkFooter.vue, SignalCard.vue, CarPhoto.vue. Estonian enum labels + body-facet→enum mapping + fairness mapping in app/utils/labels.ts.
- Price fairness is REAL: SignalCard + detail buybox call GET /v1/valuations (deal_score great/good/fair/high/unknown + pct_vs_market) via composables/useValuation.ts. NOT faked. Verification, seller rating, and history timeline are honest placeholders (no backing API data) — do not fabricate them; this respects the trust-by-default/clean-room product pillar.
- Filter facets are single-select (API body/fuel/transmission are single enums). Estonian body facets map: universaal→wagon, maastur→suv, luukpära→hatchback, sedaan→sedan, mahtuniversaal→minivan, kaubik→van.
- Known SSR nit: detail-page fairness chip and "Sarnased autod" populate after client hydration (dependent-fetch timing — they depend on the listing resolving), not in initial SSR HTML.
