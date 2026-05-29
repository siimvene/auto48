<script setup lang="ts">
import type { ListingCreate, VehicleLookup, FuelType, BodyType, TransmissionType, DrivetrainType } from '~/types/listing'

useSeoMeta({
  title: 'Lisa kuulutus — auto48',
  description: 'Lisa oma auto kuulutus 60 sekundiga. Täida mark, mudel ja andmed numbrimärgi järgi automaatselt. Eraisikule tasuta.',
})

const config = useRuntimeConfig()
const { isLoggedIn, authHeaders } = useAuth()

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
      lookupError.value = 'Numbrimärki ei leitud. Palun täida andmed käsitsi.'
    } else if (status === 503 || status === 501 || !status) {
      lookupError.value = 'Automaatne täitmine pole veel saadaval — palun täida käsitsi.'
    } else {
      lookupError.value = 'Otsing ebaõnnestus. Palun täida andmed käsitsi.'
    }
  } finally {
    lookupPending.value = false
  }
}

// ---------------------------------------------------------------------------
// Form state
// ---------------------------------------------------------------------------
interface FormState {
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

  if (!form.title.trim())         e.title        = 'Pealkiri on kohustuslik'
  if (!form.make.trim())          e.make         = 'Mark on kohustuslik'
  if (!form.model.trim())         e.model        = 'Mudel on kohustuslik'
  if (!form.year || isNaN(Number(form.year)) || Number(form.year) < 1900 || Number(form.year) > new Date().getFullYear() + 1)
                                  e.year         = 'Sisesta kehtiv aasta'
  if (!form.price_eur || isNaN(Number(form.price_eur)) || Number(form.price_eur) < 1)
                                  e.price_eur    = 'Sisesta kehtiv hind'
  if (!form.fuel)                 e.fuel         = 'Kütus on kohustuslik'
  if (!form.body)                 e.body         = 'Keretüüp on kohustuslik'
  if (!form.transmission)         e.transmission = 'Käigukast on kohustuslik'
  if (!form.location_county.trim()) e.location_county = 'Asukoht on kohustuslik'

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

  const payload: Omit<ListingCreate, 'seller_id'> = {
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
      headers: authHeaders(),
      body: payload,
    })
    await router.push(`/listings/${created.id}`)
  } catch (err: unknown) {
    const status = (err as { statusCode?: number })?.statusCode
    if (status === 422) {
      submitError.value = 'Mõned väljad on vigased. Palun kontrolli sisestust.'
    } else if (status === 401 || status === 403) {
      await router.push('/login?redirect=/sell')
    } else {
      submitError.value = 'Kuulutuse loomine ebaõnnestus. Palun proovi hiljem uuesti.'
    }
  } finally {
    submitPending.value = false
  }
}

// ---------------------------------------------------------------------------
// Options — values MUST match backend enums exactly
// ---------------------------------------------------------------------------
const fuelOptions = [
  { value: 'petrol',        label: 'Bensiin' },
  { value: 'diesel',        label: 'Diisel' },
  { value: 'electric',      label: 'Elektri' },
  { value: 'hybrid',        label: 'Hübriid' },
  { value: 'plugin_hybrid', label: 'Pistikhübriid' },
  { value: 'lpg',           label: 'Gaas (LPG)' },
  { value: 'cng',           label: 'Gaas (CNG)' },
  { value: 'other',         label: 'Muu' },
]

const bodyOptions = [
  { value: 'sedan',       label: 'Sedaan' },
  { value: 'hatchback',   label: 'Luukpära' },
  { value: 'wagon',       label: 'Universaal' },
  { value: 'suv',         label: 'Maastur' },
  { value: 'coupe',       label: 'Kupee' },
  { value: 'convertible', label: 'Kabriolett' },
  { value: 'minivan',     label: 'Mahtuniversaal' },
  { value: 'pickup',      label: 'Pikap' },
  { value: 'van',         label: 'Kaubik' },
  { value: 'other',       label: 'Muu' },
]

const transmissionOptions = [
  { value: 'manual',        label: 'Manuaal' },
  { value: 'automatic',     label: 'Automaat' },
  { value: 'semi_automatic', label: 'Poolautomaat' },
  { value: 'cvt',           label: 'Astmeteta (CVT)' },
]

const drivetrainOptions = [
  { value: 'fwd', label: 'Esivedu' },
  { value: 'rwd', label: 'Tagavedu' },
  { value: 'awd', label: 'Nelikvedu' },
]

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 35 }, (_, i) => currentYear - i)
</script>

<template>
  <div>
    <LightNav />
    <div class="sell-page__inner">
      <!-- Header -->
      <header class="sell-header">
        <h1 class="sell-header__title">Lisa kuulutus 60 sekundiga</h1>
        <p class="sell-header__sub">Eraisikule tasuta. Täida andmed numbrimärgi järgi automaatselt ja avalda minutitega.</p>
      </header>

      <!-- Auth gate: show CTA when not logged in instead of the form -->
      <div v-if="!isLoggedIn" class="auth-gate">
        <div class="auth-gate__icon" aria-hidden="true"><Icon name="lock" :size="28" /></div>
        <h2 class="auth-gate__title">Logi sisse, et kuulutus lisada</h2>
        <p class="auth-gate__text">Kuulutuse loomiseks peab olema sisse logitud. Eraisikule tasuta.</p>
        <NuxtLink to="/login?redirect=/sell" class="btn-volt auth-gate__cta">
          <Icon name="log-in" :size="16" />
          Logi sisse
        </NuxtLink>
        <p class="auth-gate__reg">Pole kontot? <NuxtLink to="/register?redirect=/sell">Registreeru</NuxtLink></p>
      </div>

      <!-- Plate lookup -->
      <section v-if="isLoggedIn" class="lookup-section" aria-label="Auto-fill from plate">
        <div class="lookup-card">
          <div class="lookup-card__icon" aria-hidden="true"><Icon name="search" :size="22" /></div>
          <div class="lookup-card__body">
            <p class="lookup-card__title">Täida automaatselt numbrimärgi või VIN-i järgi</p>
            <p class="lookup-card__desc">Sisesta numbrimärk ja täidame margi, mudeli, aasta ning tehnilised andmed sinu eest.</p>
          </div>
          <div class="lookup-card__input">
            <div class="lookup-input-group" role="group" aria-label="Plate lookup">
              <input
                v-model="plateInput"
                class="lookup-input"
                type="text"
                placeholder="nt 123ABC"
                aria-label="Numbrimärk"
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
                {{ lookupPending ? 'Otsin…' : 'Otsi andmed' }}
              </button>
            </div>
            <p v-if="lookupError" class="lookup-error" role="alert">{{ lookupError }}</p>
            <p v-else-if="lookupSuccess" class="lookup-success" role="status">Andmed täidetud — kontrolli ja täienda allpool.</p>
          </div>
        </div>
      </section>

      <!-- Listing form -->
      <form v-if="isLoggedIn" class="listing-form" novalidate @submit.prevent="submitListing">

        <!-- Basic info -->
        <section class="form-section">
          <h2 class="form-section__title">Põhiandmed</h2>

          <div class="form-grid">
            <div class="field field--full">
              <label class="field__label" for="title">Kuulutuse pealkiri <span class="required" aria-hidden="true">*</span></label>
              <input
                id="title"
                v-model="form.title"
                class="field__input"
                :class="{ 'field__input--error': errors.title }"
                type="text"
                placeholder="nt Toyota Corolla 2019 — üks omanik, täielik hooldusajalugu"
                maxlength="120"
                required
                aria-required="true"
                :aria-describedby="errors.title ? 'title-error' : undefined"
                @input="clearError('title')"
              />
              <p v-if="errors.title" id="title-error" class="field__error" role="alert">{{ errors.title }}</p>
            </div>

            <div class="field">
              <label class="field__label" for="make">Mark <span class="required" aria-hidden="true">*</span></label>
              <input
                id="make"
                v-model="form.make"
                class="field__input"
                :class="{ 'field__input--error': errors.make }"
                type="text"
                placeholder="nt Toyota"
                required
                @input="clearError('make')"
              />
              <p v-if="errors.make" class="field__error" role="alert">{{ errors.make }}</p>
            </div>

            <div class="field">
              <label class="field__label" for="model">Mudel <span class="required" aria-hidden="true">*</span></label>
              <input
                id="model"
                v-model="form.model"
                class="field__input"
                :class="{ 'field__input--error': errors.model }"
                type="text"
                placeholder="nt Corolla"
                required
                @input="clearError('model')"
              />
              <p v-if="errors.model" class="field__error" role="alert">{{ errors.model }}</p>
            </div>

            <div class="field">
              <label class="field__label" for="variant">Varustustase</label>
              <input
                id="variant"
                v-model="form.variant"
                class="field__input"
                type="text"
                placeholder="nt 1.8 Hybrid Executive"
              />
            </div>

            <div class="field">
              <label class="field__label" for="year">Aasta <span class="required" aria-hidden="true">*</span></label>
              <select
                id="year"
                v-model="form.year"
                class="field__input field__select"
                :class="{ 'field__input--error': errors.year }"
                required
                @change="clearError('year')"
              >
                <option value="">Vali aasta</option>
                <option v-for="y in yearOptions" :key="y" :value="String(y)">{{ y }}</option>
              </select>
              <p v-if="errors.year" class="field__error" role="alert">{{ errors.year }}</p>
            </div>
          </div>
        </section>

        <!-- Price & mileage -->
        <section class="form-section">
          <h2 class="form-section__title">Hind ja läbisõit</h2>
          <div class="form-grid">
            <div class="field">
              <label class="field__label" for="price">Hind (€) <span class="required" aria-hidden="true">*</span></label>
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
                  placeholder="nt 12500"
                  required
                  aria-describedby="price-prefix"
                  @input="clearError('price_eur')"
                />
                <span id="price-prefix" class="field__input-addon" aria-hidden="true">€</span>
              </div>
              <p v-if="errors.price_eur" class="field__error" role="alert">{{ errors.price_eur }}</p>
            </div>

            <div class="field">
              <label class="field__label" for="mileage">Läbisõit (km)</label>
              <input
                id="mileage"
                v-model="form.mileage_km"
                class="field__input"
                type="number"
                min="0"
                max="2000000"
                placeholder="nt 87000"
              />
            </div>
          </div>
        </section>

        <!-- Vehicle specs -->
        <section class="form-section">
          <h2 class="form-section__title">Tehnilised andmed</h2>
          <div class="form-grid">
            <div class="field">
              <label class="field__label" for="fuel">Kütus <span class="required" aria-hidden="true">*</span></label>
              <select
                id="fuel"
                v-model="form.fuel"
                class="field__input field__select"
                :class="{ 'field__input--error': errors.fuel }"
                required
                @change="clearError('fuel')"
              >
                <option value="">Vali kütus</option>
                <option v-for="opt in fuelOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
              <p v-if="errors.fuel" class="field__error" role="alert">{{ errors.fuel }}</p>
            </div>

            <div class="field">
              <label class="field__label" for="body">Keretüüp <span class="required" aria-hidden="true">*</span></label>
              <select
                id="body"
                v-model="form.body"
                class="field__input field__select"
                :class="{ 'field__input--error': errors.body }"
                required
                @change="clearError('body')"
              >
                <option value="">Vali keretüüp</option>
                <option v-for="opt in bodyOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
              <p v-if="errors.body" class="field__error" role="alert">{{ errors.body }}</p>
            </div>

            <div class="field">
              <label class="field__label" for="transmission">Käigukast <span class="required" aria-hidden="true">*</span></label>
              <select
                id="transmission"
                v-model="form.transmission"
                class="field__input field__select"
                :class="{ 'field__input--error': errors.transmission }"
                required
                @change="clearError('transmission')"
              >
                <option value="">Vali käigukast</option>
                <option v-for="opt in transmissionOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
              <p v-if="errors.transmission" class="field__error" role="alert">{{ errors.transmission }}</p>
            </div>

            <div class="field">
              <label class="field__label" for="drivetrain">Vedu</label>
              <select
                id="drivetrain"
                v-model="form.drivetrain"
                class="field__input field__select"
              >
                <option value="">Teadmata / määramata</option>
                <option v-for="opt in drivetrainOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>
          </div>
        </section>

        <!-- Location & description -->
        <section class="form-section">
          <h2 class="form-section__title">Asukoht ja kirjeldus</h2>
          <div class="form-grid">
            <div class="field">
              <label class="field__label" for="location_county">Asukoht <span class="required" aria-hidden="true">*</span></label>
              <input
                id="location_county"
                v-model="form.location_county"
                class="field__input"
                :class="{ 'field__input--error': errors.location_county }"
                type="text"
                placeholder="nt Tallinn, Harjumaa"
                required
                @input="clearError('location_county')"
              />
              <p v-if="errors.location_county" class="field__error" role="alert">{{ errors.location_county }}</p>
            </div>

            <div class="field field--full">
              <label class="field__label" for="description">Kirjeldus</label>
              <textarea
                id="description"
                v-model="form.description"
                class="field__input field__textarea"
                rows="5"
                placeholder="Kirjelda auto seisukorda, ajalugu, hiljutisi hooldustöid ja lisavarustust…"
                maxlength="4000"
              />
              <p class="field__hint">{{ form.description.length }} / 4000 tähemärki</p>
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
            {{ submitPending ? 'Avaldan…' : 'Avalda kuulutus' }}
          </button>
          <p class="form-footer__note">Eraisikule tasuta. Ei mingeid varjatud tasusid.</p>
        </div>
      </form>
    </div>
    <DarkFooter />
  </div>
</template>

<style scoped>
.sell-page__inner {
  max-width: 760px;
  margin: 0 auto;
  padding: 32px 20px 64px;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

/* ---- Auth gate ---- */
.auth-gate {
  background: var(--surface);
  border: 1px solid var(--line-l);
  border-radius: 18px;
  padding: 48px 32px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
}
.auth-gate__icon {
  width: 56px; height: 56px; border-radius: 14px;
  background: var(--page); color: var(--faint-l);
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 4px;
}
.auth-gate__title {
  font-family: var(--space); font-size: 22px; font-weight: 700;
  letter-spacing: -.02em; color: var(--ink); margin: 0;
}
.auth-gate__text { font-size: 15px; color: var(--muted-l); margin: 0; max-width: 340px; }
.auth-gate__cta { margin-top: 8px; }
.auth-gate__reg { font-size: 14px; color: var(--muted-l); margin: 0; }
.auth-gate__reg a { color: var(--ink); font-weight: 600; text-decoration: none; }
.auth-gate__reg a:hover { text-decoration: underline; }

/* ---- Header ---- */
.sell-header__title {
  font-family: var(--space);
  font-size: 34px;
  font-weight: 700;
  letter-spacing: -.025em;
  color: var(--ink);
  margin: 0 0 8px;
}
.sell-header__sub { font-size: 16px; color: var(--muted-l); margin: 0; }

/* ---- Lookup card ---- */
.lookup-card {
  background: var(--night);
  color: #F3F7EC;
  border: 1px solid var(--line-d);
  border-radius: 16px;
  padding: 22px;
  display: flex;
  gap: 18px;
  align-items: flex-start;
  flex-wrap: wrap;
}
.lookup-card__icon {
  width: 44px; height: 44px; border-radius: 11px; flex-shrink: 0;
  background: rgba(194, 238, 69, .14); color: var(--volt);
  display: flex; align-items: center; justify-content: center;
}
.lookup-card__body { flex: 1; min-width: 220px; }
.lookup-card__title { font-family: var(--space); font-size: 16px; font-weight: 600; color: #F3F7EC; margin: 0 0 4px; }
.lookup-card__desc { font-size: 13.5px; color: var(--muted-d); margin: 0; }
.lookup-card__input { flex: 1; min-width: 240px; display: flex; flex-direction: column; gap: 8px; }
.lookup-input-group { display: flex; gap: 8px; }
.lookup-input {
  flex: 1; padding: 11px 14px; border-radius: 10px; border: 1px solid var(--line-d);
  background: var(--night-2); color: #F3F7EC; font: inherit; font-size: 15px;
  text-transform: uppercase; letter-spacing: .08em; transition: border-color .2s, box-shadow .2s;
}
.lookup-input::placeholder { color: var(--faint-d); letter-spacing: normal; text-transform: none; }
.lookup-input:focus { outline: none; border-color: rgba(194, 238, 69, .5); box-shadow: 0 0 0 3px rgba(194, 238, 69, .12); }
.lookup-error { font-size: 13px; color: #F2A98F; margin: 0; }
.lookup-success { font-size: 13px; color: var(--volt); margin: 0; }

/* ---- Form sections ---- */
.listing-form { display: flex; flex-direction: column; gap: 16px; }
.form-section {
  background: var(--surface); border: 1px solid var(--line-l); border-radius: 16px; padding: 24px 26px;
}
.form-section__title {
  font-family: var(--mono); font-size: 11.5px; font-weight: 600; letter-spacing: .08em;
  text-transform: uppercase; color: var(--faint-l); margin: 0 0 18px;
}
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 560px) { .form-grid { grid-template-columns: 1fr; } }

.field { display: flex; flex-direction: column; gap: 6px; }
.field--full { grid-column: 1 / -1; }
.field__label { font-size: 13.5px; font-weight: 600; color: var(--ink); }
.required { color: var(--neg); }

.field__input {
  padding: 11px 14px; border: 1px solid var(--line-l); border-radius: 10px; font: inherit; font-size: 15px;
  color: var(--ink); background: var(--page); transition: border-color .2s, box-shadow .2s, background .2s;
  width: 100%; box-sizing: border-box;
}
.field__input:focus {
  outline: none; border-color: var(--volt-2); box-shadow: 0 0 0 3px rgba(174, 224, 43, .16); background: var(--surface);
}
.field__input--error { border-color: var(--neg); background: rgba(192, 73, 43, .06); }
.field__select { cursor: pointer; }
.field__textarea { resize: vertical; min-height: 130px; line-height: 1.6; }
.field__input-group { position: relative; display: flex; align-items: center; }
.field__input--prefix { padding-right: 2rem; }
.field__input-addon { position: absolute; right: 14px; font-size: 15px; color: var(--faint-l); pointer-events: none; }
.field__error { font-size: 12.5px; color: var(--neg); margin: 0; }
.field__hint { font-size: 12px; color: var(--faint-l); text-align: right; margin: 0; }

/* ---- Form footer ---- */
.form-footer { display: flex; flex-direction: column; align-items: center; gap: 12px; padding-top: 4px; }
.submit-error {
  font-size: 14px; color: var(--neg); text-align: center; margin: 0; padding: 12px 16px;
  background: rgba(192, 73, 43, .07); border: 1px solid rgba(192, 73, 43, .3); border-radius: 10px;
  width: 100%; box-sizing: border-box;
}
.form-footer__note { font-size: 13px; color: var(--faint-l); margin: 0; }

/* ---- Buttons (page-local variants on top of global btn-* ) ---- */
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px; font-weight: 700;
  border-radius: 11px; cursor: pointer; border: none; text-decoration: none; font-family: inherit;
  transition: background .2s, transform .15s, opacity .2s;
}
.btn:disabled { opacity: .55; cursor: not-allowed; }
.btn--primary { background: var(--volt); color: var(--volt-ink); padding: 12px 22px; font-size: 15px; }
.btn--primary:hover:not(:disabled) { background: var(--volt-2); transform: translateY(-1px); }
.btn--secondary {
  background: var(--volt); color: var(--volt-ink); padding: 10px 16px; font-size: 14px; white-space: nowrap;
}
.btn--secondary:hover:not(:disabled) { background: var(--volt-2); }
.btn--lg { padding: 15px 40px; font-size: 16px; }

/* ---- Spinner ---- */
@keyframes spin { to { transform: rotate(360deg); } }
.spinner {
  display: inline-block; width: 1em; height: 1em; border: 2px solid currentColor;
  border-top-color: transparent; border-radius: 50%; animation: spin .7s linear infinite; flex-shrink: 0;
}
</style>
