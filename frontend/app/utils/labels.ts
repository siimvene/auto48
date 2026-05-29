/**
 * Estonian display labels and icon mappings for API enum values.
 * The API stores English enums (diesel, wagon, automatic …); the Signal
 * design displays Estonian. Keep these in sync with src/auto48/models/vehicle.py.
 */
import type { BodyType, FuelType, TransmissionType, DrivetrainType } from '~/types/listing'

export const fuelLabel: Record<FuelType, string> = {
  petrol: 'Bensiin',
  diesel: 'Diisel',
  hybrid: 'Hübriid',
  plugin_hybrid: 'Pistikhübriid',
  electric: 'Elektri',
  lpg: 'Gaas (LPG)',
  cng: 'Gaas (CNG)',
  other: 'Muu',
}

export const bodyLabel: Record<BodyType, string> = {
  sedan: 'Sedaan',
  hatchback: 'Luukpära',
  wagon: 'Universaal',
  suv: 'Maastur',
  coupe: 'Kupee',
  convertible: 'Kabriolett',
  minivan: 'Mahtuniversaal',
  pickup: 'Pikap',
  van: 'Kaubik',
  other: 'Muu',
}

export const transmissionLabel: Record<TransmissionType, string> = {
  manual: 'Manuaal',
  automatic: 'Automaat',
  semi_automatic: 'Poolautomaat',
  cvt: 'Astmeteta (CVT)',
}

export const drivetrainLabel: Record<DrivetrainType, string> = {
  fwd: 'Esivedu',
  rwd: 'Tagavedu',
  awd: 'Nelikvedu',
}

/** Lucide icon name per fuel type. */
export const fuelIcon: Record<FuelType, string> = {
  petrol: 'fuel',
  diesel: 'fuel',
  hybrid: 'leaf',
  plugin_hybrid: 'leaf',
  electric: 'zap',
  lpg: 'flame',
  cng: 'flame',
  other: 'fuel',
}

/** Body-type categories for the home rail and the search filter sidebar. */
export interface BodyCategory {
  id: BodyType
  label: string
  icon: string
}

export const bodyCategories: BodyCategory[] = [
  { id: 'wagon', label: 'Universaal', icon: 'caravan' },
  { id: 'suv', label: 'Maastur', icon: 'car-front' },
  { id: 'hatchback', label: 'Luukpära', icon: 'car' },
  { id: 'sedan', label: 'Sedaan', icon: 'car-taxi-front' },
  { id: 'minivan', label: 'Mahtuniversaal', icon: 'bus' },
  { id: 'van', label: 'Kaubik', icon: 'truck' },
]

// ---------------------------------------------------------------------------
// Fairness — derived from the real /v1/valuations deal_score + pct_vs_market.
// ---------------------------------------------------------------------------
export type DealScore = 'great' | 'good' | 'fair' | 'high' | 'unknown'

export interface Fairness {
  key: DealScore
  /** Short label for the card chip. */
  short: string
  /** Longer label for the detail buybox. */
  label: string
  /** Lucide icon name. */
  icon: string
  /** Whole-percent deviation vs market (absolute value), or null. */
  pct: number | null
}

/**
 * Map a valuation deal_score + pct_vs_market (fraction, e.g. -0.12) into the
 * design's fairness chip. pct_vs_market is negative when below market.
 */
export function toFairness(
  deal: DealScore | null | undefined,
  pctVsMarket: number | null | undefined,
): Fairness {
  const pct = pctVsMarket == null ? null : Math.round(Math.abs(pctVsMarket) * 100)
  switch (deal) {
    case 'great':
    case 'good':
      return {
        key: deal,
        short: pct != null ? `${pct}% alla turu` : 'Alla turuhinna',
        label: 'Alla turuhinna',
        icon: 'trending-down',
        pct,
      }
    case 'high':
      return {
        key: 'high',
        short: 'Üle turu',
        label: 'Üle turuhinna',
        icon: 'trending-up',
        pct,
      }
    case 'fair':
      return {
        key: 'fair',
        short: 'Õiglane hind',
        label: 'Õiglane hind',
        icon: 'check-circle',
        pct,
      }
    default:
      return {
        key: 'unknown',
        short: 'Hind hindamisel',
        label: 'Hind hindamisel',
        icon: 'circle-help',
        pct: null,
      }
  }
}

/** Deterministic dark gradient for photo placeholders, seeded by id. */
export function placeholderGradient(seed: number): string {
  const hue = (seed * 47) % 360
  return `linear-gradient(150deg, hsl(${hue} 16% 30%), hsl(${(hue + 20) % 360} 20% 17%))`
}

/** Simple financing estimate: 20% down, 5yr, ~6.9% APR. Input/output in cents. */
export function monthlyEstimateCents(priceCents: number): number {
  const p = priceCents * 0.8
  const r = 0.069 / 12
  const n = 60
  return Math.round((p * r) / (1 - Math.pow(1 + r, -n)))
}
