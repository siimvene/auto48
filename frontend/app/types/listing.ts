/**
 * TypeScript interfaces matching the auto48 v1 API contract.
 * All money values are integer cents (EUR). Use formatEur() for display.
 */

// Values MUST match the backend enums in src/auto48/models/vehicle.py.
export type FuelType = 'petrol' | 'diesel' | 'hybrid' | 'plugin_hybrid' | 'electric' | 'lpg' | 'cng' | 'other'
export type BodyType = 'sedan' | 'hatchback' | 'wagon' | 'suv' | 'coupe' | 'convertible' | 'minivan' | 'pickup' | 'van' | 'other'
export type TransmissionType = 'manual' | 'automatic' | 'semi_automatic' | 'cvt'
export type DrivetrainType = 'fwd' | 'rwd' | 'awd'
export type ListingStatus = 'draft' | 'active' | 'sold' | 'expired'

/** Nested vehicle object as returned within a ListingResponse. */
export interface Vehicle {
  id: number
  vin?: string
  plate?: string
  make: string
  model: string
  variant?: string
  year: number
  fuel: FuelType
  body: BodyType
  transmission: TransmissionType
  drivetrain?: DrivetrainType
  specs?: Record<string, unknown>
}

/** A single photo attached to a listing. `url` is a CDN-absolute URL. */
export interface Photo {
  id: number
  listing_id: number
  url: string
  position: number
  processed: boolean
  created_at: string
}

/**
 * Full listing as returned by GET /v1/listings/{id} and items in GET /v1/listings.
 * Vehicle specs are in the nested `vehicle` object; photos are NOT embedded —
 * fetch separately via GET /v1/listings/{id}/photos.
 */
export interface Listing {
  id: number
  seller_id: number
  vehicle_id: number
  title: string
  description?: string
  /** Price in integer cents EUR */
  price_eur_cents: number
  mileage_km?: number | null
  location_county?: string
  lat?: number
  lon?: number
  status: ListingStatus
  vehicle: Vehicle
  /** ISO 8601 datetime */
  created_at: string
  /** ISO 8601 datetime */
  updated_at: string
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
  /** Price filters are in cents */
  price_min?: number
  price_max?: number
  mileage_max?: number
  fuel?: FuelType
  body?: BodyType
  transmission?: TransmissionType
  /** Plain location string, NOT location_county */
  location?: string
  q?: string
  sort?: 'newest' | 'price_asc' | 'price_desc' | 'year_desc' | 'mileage_asc'
  limit?: number
  offset?: number
}

/** Result from GET /v1/vehicles/lookup?plate= or ?vin= */
export interface VehicleLookup {
  make?: string
  model?: string
  variant?: string
  year?: number
  fuel?: FuelType
  body?: BodyType
  transmission?: TransmissionType
  drivetrain?: DrivetrainType
  engine_cc?: number
  power_kw?: number
  color?: string
  first_registered?: string
}

/** Nested vehicle sub-object for POST /v1/listings */
export interface VehicleCreate {
  make: string
  model: string
  variant?: string
  year: number
  fuel: FuelType
  body: BodyType
  transmission: TransmissionType
  drivetrain?: DrivetrainType
  vin?: string
  plate?: string
  specs?: Record<string, unknown>
}

/** Payload for POST /v1/listings */
export interface ListingCreate {
  seller_id: number
  vehicle: VehicleCreate
  title: string
  description?: string
  /** Price in integer cents EUR */
  price_eur_cents: number
  mileage_km?: number | null
  location_county?: string
  lat?: number
  lon?: number
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
