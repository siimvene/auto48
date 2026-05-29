/**
 * TypeScript interfaces matching the auto48 v1 API contract.
 * All money values are integer cents (EUR). Use formatEur() for display.
 */

// Values MUST match the backend enums in src/auto48/models/vehicle.py.
export type FuelType = 'petrol' | 'diesel' | 'hybrid' | 'plugin_hybrid' | 'electric' | 'lpg' | 'cng' | 'other'
export type BodyType = 'sedan' | 'hatchback' | 'wagon' | 'suv' | 'coupe' | 'convertible' | 'minivan' | 'pickup' | 'van' | 'other'
export type TransmissionType = 'manual' | 'automatic' | 'semi_automatic' | 'cvt'
export type ListingStatus = 'draft' | 'active' | 'sold' | 'expired'

/** A single photo attached to a listing. `url` is a CDN-absolute URL. */
export interface Photo {
  id: number
  url: string
  thumbnail_url: string
  position: number
  processed: boolean
}

/** Full listing as returned by GET /v1/listings/{id} */
export interface Listing {
  id: number
  title: string
  make: string
  model: string
  variant?: string
  year: number
  /** Price in integer cents EUR */
  price_eur: number
  mileage_km: number | null
  fuel: FuelType
  body: BodyType
  transmission: TransmissionType
  drivetrain?: string
  location: string
  status: ListingStatus
  description?: string
  photos: Photo[]
  /** ISO 8601 datetime */
  created_at: string
  /** ISO 8601 datetime */
  updated_at: string
}

/** Lightweight listing card returned by GET /v1/listings (list view) */
export interface ListingCard {
  id: number
  title: string
  make: string
  model: string
  year: number
  /** Price in integer cents EUR */
  price_eur: number
  mileage_km: number | null
  fuel: FuelType
  body: BodyType
  transmission: TransmissionType
  location: string
  status: ListingStatus
  thumbnail_url: string | null
  created_at: string
}

/** Paginated envelope used by all list endpoints */
export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

/** Query parameters for GET /v1/listings */
export interface ListingsQuery {
  make?: string
  model?: string
  year_min?: number
  year_max?: number
  price_min?: number
  price_max?: number
  mileage_max?: number
  fuel?: FuelType
  body?: BodyType
  transmission?: TransmissionType
  location?: string
  q?: string
  limit?: number
  offset?: number
}

/** Result from GET /v1/vehicles/lookup?plate= */
export interface VehicleLookup {
  plate?: string
  vin?: string
  make?: string
  model?: string
  variant?: string
  year?: number
  fuel?: FuelType
  body?: BodyType
  transmission?: TransmissionType
  drivetrain?: string
  engine_cc?: number
  power_kw?: number
  color?: string
  first_registered?: string
}

/** Payload for POST /v1/listings */
export interface CreateListingPayload {
  title: string
  make: string
  model: string
  variant?: string
  year: number
  price_eur: number
  mileage_km?: number | null
  fuel: FuelType
  body: BodyType
  transmission: TransmissionType
  drivetrain?: string
  location: string
  description?: string
  plate?: string
  vin?: string
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Format integer cents as a localised EUR price string.
 * e.g. formatEur(1549900) → "15 499 €"
 */
export function formatEur(cents: number): string {
  return (cents / 100).toLocaleString('et-EE', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })
}

/**
 * Format mileage with locale-appropriate thousands separator.
 * Returns "—" when null/undefined.
 */
export function formatMileage(km: number | null | undefined): string {
  if (km == null) return '—'
  return km.toLocaleString('et-EE') + ' km'
}
