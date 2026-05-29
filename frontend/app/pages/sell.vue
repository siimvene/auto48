<script setup lang="ts">
import type { ListingCreate, VehicleLookup, FuelType, BodyType, TransmissionType, DrivetrainType } from '~/types/listing'

useSeoMeta({
  title: 'Sell your car — auto48',
  description: 'List your car in 60 seconds. Auto-fill make, model and specs from your plate number. Free for private sellers.',
})

const config = useRuntimeConfig()

// ---------------------------------------------------------------------------
// Plate lookup
// ---------------------------------------------------------------------------
const plateInput = ref('')
const lookupPending = ref(false)
const lookupError = ref<string | null>(null)
const lookupSuccess = ref(false)

async function lookupVehicle() {
  const plate = plateInput.value.trim().toUpperCase()
  if (!plate) return

  lookupPending.value = true
  lookupError.value = null
  lookupSuccess.value = false

  try {
    const result = await $fetch<VehicleLookup>(
      `/v1/vehicles/lookup`,
      {
        baseURL: config.public.apiBase,
        query: { plate },
      },
    )
    // Auto-fill form fields from lookup result (VehicleDataResponse → form fields)
    if (result.make)         form.make         = result.make
    if (result.model)        form.model        = result.model
    if (result.variant)      form.variant      = result.variant
    if (result.year)         form.year         = String(result.year)
    if (result.fuel)         form.fuel         = result.fuel
    if (result.body)         form.body         = result.body
    if (result.transmission) form.transmission = result.transmission
    if (result.drivetrain)   form.drivetrain   = result.drivetrain
    form.plate = plate
    lookupSuccess.value = true
  } catch (err: unknown) {
    // Graceful degradation: if the endpoint doesn't exist yet or returns 404/5xx,
    // we just let the user fill in the fields manually — never block the form.
    const status = (err as { statusCode?: number; status?: number })?.statusCode
      ?? (err as { status?: number })?.status
    if (status === 404) {
      lookupError.value = 'Plate not found. Please fill in the details manually.'
    } else if (status === 503 || status === 501 || !status) {
      lookupError.value = 'Auto-fill is not available yet — please fill in manually.'
    } else {
      lookupError.value = 'Look-up failed. Please fill in the details manually.'
    }
  } finally {
    lookupPending.value = false
  }
}

// ---------------------------------------------------------------------------
// Form state
// ---------------------------------------------------------------------------
interface FormState {
  seller_id: string
  title: string
  make: string
  model: string
  variant: string
  year: string
  price_eur: string
  mileage_km: string
  fuel: string
  body: string
  transmission: string
  drivetrain: string
  location_county: string
  description: string
  plate: string
}

const form = reactive<FormState>({
  seller_id: '',
  title: '',
  make: '',
  model: '',
  variant: '',
  year: '',
  price_eur: '',
  mileage_km: '',
  fuel: '',
  body: '',
  transmission: '',
  drivetrain: '',
  location_county: '',
  description: '',
  plate: plateInput.value,
})

// Auto-generate title when make/model/year fill in
watch([() => form.make, () => form.model, () => form.year], ([make, model, year]) => {
  if (make && model && year && !form.title) {
    form.title = `${make} ${model} ${year}`
  }
})

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------
interface ValidationErrors {
  seller_id?: string
  title?: string
  make?: string
  model?: string
  year?: string
  price_eur?: string
  fuel?: string
  body?: string
  transmission?: string
  location_county?: string
}

const errors = reactive<ValidationErrors>({})
const submitError = ref<string | null>(null)
const submitPending = ref(false)

function validate(): boolean {
  const e: ValidationErrors = {}

  if (!form.seller_id || isNaN(Number(form.seller_id)) || Number(form.seller_id) < 1)
                                  e.seller_id    = 'Seller ID is required'
  if (!form.title.trim())         e.title        = 'Title is required'
  if (!form.make.trim())          e.make         = 'Make is required'
  if (!form.model.trim())         e.model        = 'Model is required'
  if (!form.year || isNaN(Number(form.year)) || Number(form.year) < 1900 || Number(form.year) > new Date().getFullYear() + 1)
                                  e.year         = 'Valid year required'
  if (!form.price_eur || isNaN(Number(form.price_eur)) || Number(form.price_eur) < 1)
                                  e.price_eur    = 'Valid price required'
  if (!form.fuel)                 e.fuel         = 'Fuel type required'
  if (!form.body)                 e.body         = 'Body type required'
  if (!form.transmission)         e.transmission = 'Transmission required'
  if (!form.location_county.trim()) e.location_county = 'Location is required'

  Object.assign(errors, e)
  return Object.keys(e).length === 0
}

function clearError(field: keyof ValidationErrors) {
  delete errors[field]
}

// ---------------------------------------------------------------------------
// Submit
// ---------------------------------------------------------------------------
const router = useRouter()

async function submitListing() {
  if (!validate()) return

  submitPending.value = true
  submitError.value = null

  const payload: ListingCreate = {
    // TODO: derive from auth session once auth is wired into the frontend
    seller_id: Number(form.seller_id),
    vehicle: {
      make:         form.make.trim(),
      model:        form.model.trim(),
      variant:      form.variant.trim() || undefined,
      year:         Number(form.year),
      fuel:         form.fuel as FuelType,
      body:         form.body as BodyType,
      transmission: form.transmission as TransmissionType,
      drivetrain:   (form.drivetrain as DrivetrainType) || undefined,
      plate:        form.plate.trim() || undefined,
    },
    title:          form.title.trim(),
    description:    form.description.trim() || undefined,
    // Convert whole euros to integer cents
    price_eur_cents: Math.round(Number(form.price_eur) * 100),
    mileage_km:     form.mileage_km ? Number(form.mileage_km) : null,
    location_county: form.location_county.trim() || undefined,
  }

  try {
    const created = await $fetch<{ id: number }>('/v1/listings', {
      baseURL: config.public.apiBase,
      method: 'POST',
      body: payload,
    })
    await router.push(`/listings/${created.id}`)
  } catch (err: unknown) {
    const status = (err as { statusCode?: number })?.statusCode
    if (status === 422) {
      submitError.value = 'Some fields are invalid. Please check your input.'
    } else if (status === 401 || status === 403) {
      submitError.value = 'You must be logged in to post a listing.'
    } else {
      submitError.value = 'Could not create the listing. Please try again later.'
    }
  } finally {
    submitPending.value = false
  }
}

// ---------------------------------------------------------------------------
// Options — values MUST match backend enums exactly
// ---------------------------------------------------------------------------
const fuelOptions = [
  { value: 'petrol',        label: 'Petrol' },
  { value: 'diesel',        label: 'Diesel' },
  { value: 'electric',      label: 'Electric' },
  { value: 'hybrid',        label: 'Hybrid' },
  { value: 'plugin_hybrid', label: 'Plug-in hybrid' },
  { value: 'lpg',           label: 'LPG' },
  { value: 'cng',           label: 'CNG' },
  { value: 'other',         label: 'Other' },
]

const bodyOptions = [
  { value: 'sedan',       label: 'Sedan' },
  { value: 'hatchback',   label: 'Hatchback' },
  { value: 'wagon',       label: 'Wagon / Estate' },
  { value: 'suv',         label: 'SUV / Crossover' },
  { value: 'coupe',       label: 'Coupé' },
  { value: 'convertible', label: 'Convertible' },
  { value: 'minivan',     label: 'Minivan' },
  { value: 'pickup',      label: 'Pickup' },
  { value: 'van',         label: 'Van' },
  { value: 'other',       label: 'Other' },
]

const transmissionOptions = [
  { value: 'manual',        label: 'Manual' },
  { value: 'automatic',     label: 'Automatic' },
  { value: 'semi_automatic', label: 'Semi-automatic' },
  { value: 'cvt',           label: 'CVT' },
]

const drivetrainOptions = [
  { value: 'fwd', label: 'FWD (Front-wheel drive)' },
  { value: 'rwd', label: 'RWD (Rear-wheel drive)' },
  { value: 'awd', label: 'AWD (All-wheel drive)' },
]

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 35 }, (_, i) => currentYear - i)
</script>

<template>
  <div class="sell-page">
    <div class="sell-page__inner">
      <!-- Header -->
      <header class="sell-header">
        <h1 class="sell-header__title">List your car in 60 seconds</h1>
        <p class="sell-header__sub">Free for private sellers. Auto-fill from your plate, publish in minutes.</p>
      </header>

      <!-- Plate lookup -->
      <section class="lookup-section" aria-label="Auto-fill from plate">
        <div class="lookup-card">
          <div class="lookup-card__icon" aria-hidden="true">🔍</div>
          <div class="lookup-card__body">
            <p class="lookup-card__title">Auto-fill from plate or VIN</p>
            <p class="lookup-card__desc">Enter your plate and we'll pre-fill make, model, year and specs for you.</p>
          </div>
          <div class="lookup-card__input">
            <div class="lookup-input-group" role="group" aria-label="Plate lookup">
              <input
                v-model="plateInput"
                class="lookup-input"
                type="text"
                placeholder="e.g. 123ABC"
                aria-label="Plate number"
                maxlength="10"
                @keydown.enter.prevent="lookupVehicle"
              />
              <button
                type="button"
                class="btn btn--secondary"
                :disabled="lookupPending || !plateInput.trim()"
                @click="lookupVehicle"
              >
                <span v-if="lookupPending" class="spinner" aria-hidden="true" />
                {{ lookupPending ? 'Looking up…' : 'Look up' }}
              </button>
            </div>
            <p v-if="lookupError" class="lookup-error" role="alert">{{ lookupError }}</p>
            <p v-else-if="lookupSuccess" class="lookup-success" role="status">Fields auto-filled — check and adjust below.</p>
          </div>
        </div>
      </section>

      <!-- Listing form -->
      <form class="listing-form" novalidate @submit.prevent="submitListing">

        <!-- Seller info -->
        <section class="form-section">
          <h2 class="form-section__title">Seller information</h2>
          <div class="form-grid">
            <div class="field">
              <label class="field__label" for="seller_id">Seller ID <span class="required" aria-hidden="true">*</span></label>
              <!-- TODO: derive from auth session once auth is wired into the frontend -->
              <input
                id="seller_id"
                v-model="form.seller_id"
                class="field__input"
                :class="{ 'field__input--error': errors.seller_id }"
                type="number"
                min="1"
                placeholder="Your user ID"
                required
                @input="clearError('seller_id')"
              />
              <p v-if="errors.seller_id" class="field__error" role="alert">{{ errors.seller_id }}</p>
            </div>
          </div>
        </section>

        <!-- Basic info -->
        <section class="form-section">
          <h2 class="form-section__title">Basic information</h2>

          <div class="form-grid">
            <div class="field field--full">
              <label class="field__label" for="title">Listing title <span class="required" aria-hidden="true">*</span></label>
              <input
                id="title"
                v-model="form.title"
                class="field__input"
                :class="{ 'field__input--error': errors.title }"
                type="text"
                placeholder="e.g. Toyota Corolla 2019 — one owner, full service"
                maxlength="120"
                required
                aria-required="true"
                :aria-describedby="errors.title ? 'title-error' : undefined"
                @input="clearError('title')"
              />
              <p v-if="errors.title" id="title-error" class="field__error" role="alert">{{ errors.title }}</p>
            </div>

            <div class="field">
              <label class="field__label" for="make">Make <span class="required" aria-hidden="true">*</span></label>
              <input
                id="make"
                v-model="form.make"
                class="field__input"
                :class="{ 'field__input--error': errors.make }"
                type="text"
                placeholder="e.g. Toyota"
                required
                @input="clearError('make')"
              />
              <p v-if="errors.make" class="field__error" role="alert">{{ errors.make }}</p>
            </div>

            <div class="field">
              <label class="field__label" for="model">Model <span class="required" aria-hidden="true">*</span></label>
              <input
                id="model"
                v-model="form.model"
                class="field__input"
                :class="{ 'field__input--error': errors.model }"
                type="text"
                placeholder="e.g. Corolla"
                required
                @input="clearError('model')"
              />
              <p v-if="errors.model" class="field__error" role="alert">{{ errors.model }}</p>
            </div>

            <div class="field">
              <label class="field__label" for="variant">Variant / trim</label>
              <input
                id="variant"
                v-model="form.variant"
                class="field__input"
                type="text"
                placeholder="e.g. 1.8 Hybrid Executive"
              />
            </div>

            <div class="field">
              <label class="field__label" for="year">Year <span class="required" aria-hidden="true">*</span></label>
              <select
                id="year"
                v-model="form.year"
                class="field__input field__select"
                :class="{ 'field__input--error': errors.year }"
                required
                @change="clearError('year')"
              >
                <option value="">Select year</option>
                <option v-for="y in yearOptions" :key="y" :value="String(y)">{{ y }}</option>
              </select>
              <p v-if="errors.year" class="field__error" role="alert">{{ errors.year }}</p>
            </div>
          </div>
        </section>

        <!-- Price & mileage -->
        <section class="form-section">
          <h2 class="form-section__title">Price & mileage</h2>
          <div class="form-grid">
            <div class="field">
              <label class="field__label" for="price">Asking price (€) <span class="required" aria-hidden="true">*</span></label>
              <div class="field__input-group">
                <input
                  id="price"
                  v-model="form.price_eur"
                  class="field__input field__input--prefix"
                  :class="{ 'field__input--error': errors.price_eur }"
                  type="number"
                  min="1"
                  max="10000000"
                  step="1"
                  placeholder="e.g. 12500"
                  required
                  aria-describedby="price-prefix"
                  @input="clearError('price_eur')"
                />
                <span id="price-prefix" class="field__input-addon" aria-hidden="true">€</span>
              </div>
              <p v-if="errors.price_eur" class="field__error" role="alert">{{ errors.price_eur }}</p>
            </div>

            <div class="field">
              <label class="field__label" for="mileage">Mileage (km)</label>
              <input
                id="mileage"
                v-model="form.mileage_km"
                class="field__input"
                type="number"
                min="0"
                max="2000000"
                placeholder="e.g. 87000"
              />
            </div>
          </div>
        </section>

        <!-- Vehicle specs -->
        <section class="form-section">
          <h2 class="form-section__title">Vehicle specs</h2>
          <div class="form-grid">
            <div class="field">
              <label class="field__label" for="fuel">Fuel type <span class="required" aria-hidden="true">*</span></label>
              <select
                id="fuel"
                v-model="form.fuel"
                class="field__input field__select"
                :class="{ 'field__input--error': errors.fuel }"
                required
                @change="clearError('fuel')"
              >
                <option value="">Select fuel</option>
                <option v-for="opt in fuelOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
              <p v-if="errors.fuel" class="field__error" role="alert">{{ errors.fuel }}</p>
            </div>

            <div class="field">
              <label class="field__label" for="body">Body type <span class="required" aria-hidden="true">*</span></label>
              <select
                id="body"
                v-model="form.body"
                class="field__input field__select"
                :class="{ 'field__input--error': errors.body }"
                required
                @change="clearError('body')"
              >
                <option value="">Select body</option>
                <option v-for="opt in bodyOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
              <p v-if="errors.body" class="field__error" role="alert">{{ errors.body }}</p>
            </div>

            <div class="field">
              <label class="field__label" for="transmission">Transmission <span class="required" aria-hidden="true">*</span></label>
              <select
                id="transmission"
                v-model="form.transmission"
                class="field__input field__select"
                :class="{ 'field__input--error': errors.transmission }"
                required
                @change="clearError('transmission')"
              >
                <option value="">Select transmission</option>
                <option v-for="opt in transmissionOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
              <p v-if="errors.transmission" class="field__error" role="alert">{{ errors.transmission }}</p>
            </div>

            <div class="field">
              <label class="field__label" for="drivetrain">Drivetrain</label>
              <select
                id="drivetrain"
                v-model="form.drivetrain"
                class="field__input field__select"
              >
                <option value="">Unknown / not specified</option>
                <option v-for="opt in drivetrainOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>
          </div>
        </section>

        <!-- Location & description -->
        <section class="form-section">
          <h2 class="form-section__title">Location & description</h2>
          <div class="form-grid">
            <div class="field">
              <label class="field__label" for="location_county">Location <span class="required" aria-hidden="true">*</span></label>
              <input
                id="location_county"
                v-model="form.location_county"
                class="field__input"
                :class="{ 'field__input--error': errors.location_county }"
                type="text"
                placeholder="e.g. Tallinn, Harjumaa"
                required
                @input="clearError('location_county')"
              />
              <p v-if="errors.location_county" class="field__error" role="alert">{{ errors.location_county }}</p>
            </div>

            <div class="field field--full">
              <label class="field__label" for="description">Description</label>
              <textarea
                id="description"
                v-model="form.description"
                class="field__input field__textarea"
                rows="5"
                placeholder="Tell buyers about the car's condition, history, what's been serviced recently, any extras…"
                maxlength="4000"
              />
              <p class="field__hint">{{ form.description.length }} / 4000 characters</p>
            </div>
          </div>
        </section>

        <!-- Submit -->
        <div class="form-footer">
          <p v-if="submitError" class="submit-error" role="alert">{{ submitError }}</p>
          <button
            type="submit"
            class="btn btn--primary btn--lg"
            :disabled="submitPending"
          >
            <span v-if="submitPending" class="spinner" aria-hidden="true" />
            {{ submitPending ? 'Publishing…' : 'Publish listing' }}
          </button>
          <p class="form-footer__note">Free for private sellers. No hidden fees.</p>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.sell-page {
  background: #f9fafb;
  min-height: 100vh;
  padding: 2rem 1.25rem 4rem;
  font-family: system-ui, sans-serif;
}

.sell-page__inner {
  max-width: 760px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* ---- Header ---- */
.sell-header__title {
  font-size: 1.75rem;
  font-weight: 800;
  color: #111;
  margin: 0 0 0.35rem;
  letter-spacing: -0.02em;
}

.sell-header__sub {
  font-size: 1rem;
  color: #6b7280;
  margin: 0;
}

/* ---- Lookup card ---- */
.lookup-card {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  padding: 1.25rem;
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  flex-wrap: wrap;
}

.lookup-card__icon {
  font-size: 1.5rem;
  flex-shrink: 0;
  line-height: 1;
  margin-top: 0.1rem;
}

.lookup-card__body { flex: 1; min-width: 200px; }
.lookup-card__title { font-size: 0.95rem; font-weight: 700; color: #1e40af; margin: 0 0 0.2rem; }
.lookup-card__desc  { font-size: 0.83rem; color: #3b82f6; margin: 0; }

.lookup-card__input {
  flex: 1;
  min-width: 220px;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.lookup-input-group {
  display: flex;
  gap: 0.5rem;
}

.lookup-input {
  flex: 1;
  padding: 0.55rem 0.75rem;
  border: 1px solid #93c5fd;
  border-radius: 7px;
  font-size: 0.9rem;
  font-family: inherit;
  color: #111;
  background: #fff;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.lookup-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgb(37 99 235 / 15%);
}

.lookup-error   { font-size: 0.8rem; color: #dc2626; margin: 0; }
.lookup-success { font-size: 0.8rem; color: #166534; margin: 0; }

/* ---- Form sections ---- */
.listing-form { display: flex; flex-direction: column; gap: 1.5rem; }

.form-section {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 1.5rem;
}

.form-section__title {
  font-size: 0.9rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6b7280;
  margin: 0 0 1.25rem;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

@media (max-width: 560px) {
  .form-grid { grid-template-columns: 1fr; }
}

.field { display: flex; flex-direction: column; gap: 0.3rem; }
.field--full { grid-column: 1 / -1; }

.field__label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #374151;
}

.required { color: #dc2626; }

.field__input {
  padding: 0.575rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 7px;
  font-size: 0.9rem;
  font-family: inherit;
  color: #111;
  background: #fafafa;
  transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
  width: 100%;
  box-sizing: border-box;
}

.field__input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgb(37 99 235 / 12%);
  background: #fff;
}

.field__input--error {
  border-color: #f87171;
  background: #fff5f5;
}

.field__select { cursor: pointer; }

.field__textarea {
  resize: vertical;
  min-height: 120px;
  line-height: 1.6;
}

.field__input-group {
  position: relative;
  display: flex;
  align-items: center;
}

.field__input--prefix { padding-right: 2rem; }

.field__input-addon {
  position: absolute;
  right: 0.75rem;
  font-size: 0.9rem;
  color: #9ca3af;
  pointer-events: none;
}

.field__error {
  font-size: 0.78rem;
  color: #dc2626;
  margin: 0;
}

.field__hint {
  font-size: 0.75rem;
  color: #9ca3af;
  text-align: right;
  margin: 0;
}

/* ---- Form footer ---- */
.form-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding-top: 0.5rem;
}

.submit-error {
  font-size: 0.875rem;
  color: #dc2626;
  text-align: center;
  margin: 0;
  padding: 0.75rem 1rem;
  background: #fff5f5;
  border: 1px solid #fca5a5;
  border-radius: 8px;
  width: 100%;
  box-sizing: border-box;
}

.form-footer__note {
  font-size: 0.78rem;
  color: #9ca3af;
  margin: 0;
}

/* ---- Buttons ---- */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  border: none;
  text-decoration: none;
  transition: background 0.15s, box-shadow 0.15s;
  font-family: inherit;
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn--primary {
  background: #2563eb;
  color: #fff;
  padding: 0.7rem 1.5rem;
  font-size: 0.95rem;
}

.btn--primary:hover:not(:disabled) {
  background: #1d4ed8;
  box-shadow: 0 2px 8px rgb(37 99 235 / 30%);
}

.btn--secondary {
  background: #fff;
  color: #2563eb;
  border: 1.5px solid #2563eb;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
}

.btn--secondary:hover:not(:disabled) {
  background: #eff6ff;
}

.btn--lg {
  padding: 0.875rem 2.5rem;
  font-size: 1.05rem;
}

/* ---- Spinner ---- */
@keyframes spin { to { transform: rotate(360deg); } }

.spinner {
  display: inline-block;
  width: 1em;
  height: 1em;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}
</style>
