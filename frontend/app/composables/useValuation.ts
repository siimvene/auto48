import type { DealScore } from '~/utils/labels'

/** Response shape of GET /v1/valuations (matches ValuationResponse on the backend). */
export interface Valuation {
  estimate_eur_cents: number | null
  sample_size: number
  deal_score: DealScore
  pct_vs_market: number | null
  low_eur_cents: number | null
  high_eur_cents: number | null
}

export interface ValuationParams {
  make: string
  model: string
  year: number
  mileage_km?: number | null
  price_eur_cents?: number | null
}

const UNKNOWN: Valuation = {
  estimate_eur_cents: null,
  sample_size: 0,
  deal_score: 'unknown',
  pct_vs_market: null,
  low_eur_cents: null,
  high_eur_cents: null,
}

/**
 * Fetch a market valuation / deal-score for a vehicle once its params are known.
 *
 * Degrades gracefully: any error (endpoint down, too few comparables, missing
 * params) leaves the result as an `unknown` deal score rather than throwing —
 * the UI then shows "Hind hindamisel". Re-fetches when params change.
 */
export function useValuation(
  params: Ref<ValuationParams | null> | ComputedRef<ValuationParams | null>,
) {
  const config = useRuntimeConfig()
  const data = ref<Valuation>({ ...UNKNOWN })
  const pending = ref(false)

  async function load(p: ValuationParams) {
    pending.value = true
    try {
      data.value = await $fetch<Valuation>('/v1/valuations', {
        baseURL: config.public.apiBase,
        query: {
          make: p.make,
          model: p.model,
          year: p.year,
          ...(p.mileage_km != null ? { mileage_km: p.mileage_km } : {}),
          ...(p.price_eur_cents != null ? { price_eur_cents: p.price_eur_cents } : {}),
        },
      })
    } catch {
      data.value = { ...UNKNOWN }
    } finally {
      pending.value = false
    }
  }

  watch(
    () => toValue(params),
    (p) => {
      if (p && p.make && p.model && p.year) load(p)
      else data.value = { ...UNKNOWN }
    },
    { immediate: true },
  )

  const fairness = computed(() => toFairness(data.value.deal_score, data.value.pct_vs_market))

  return { data, fairness, pending }
}
