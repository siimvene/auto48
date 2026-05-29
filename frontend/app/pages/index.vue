<script setup lang="ts">
import { useListings } from '~/composables/useListings'
import type { ListingsQuery, BodyType, FuelType, TransmissionType } from '~/types/listing'
import { formatEur, formatMileage } from '~/types/listing'

useSeoMeta({
  title: 'auto48 — Buy and sell cars in Estonia',
  description: 'Trusted car marketplace with verified vehicle history. Find your next car or list yours in 60 seconds.',
})

const route = useRoute()
const router = useRouter()

// ---------------------------------------------------------------------------
// Filter state — initialised from URL query so SSR and client agree
// ---------------------------------------------------------------------------
const filterMake = ref<string>((route.query.make as string) ?? '')
const filterModel = ref<string>((route.query.model as string) ?? '')
const filterYearMin = ref<string>((route.query.year_min as string) ?? '')
const filterYearMax = ref<string>((route.query.year_max as string) ?? '')
const filterPriceMin = ref<string>((route.query.price_min as string) ?? '')
const filterPriceMax = ref<string>((route.query.price_max as string) ?? '')
const filterFuel = ref<string>((route.query.fuel as string) ?? '')
const filterBody = ref<string>((route.query.body as string) ?? '')
const filterTransmission = ref<string>((route.query.transmission as string) ?? '')
const filterLocation = ref<string>((route.query.location as string) ?? '')
const PAGE_SIZE = 24
const currentPage = ref<number>(Number(route.query.page ?? 1))

// ---------------------------------------------------------------------------
// Reactive API query — drives refetch automatically
// ---------------------------------------------------------------------------
const apiQuery = computed((): ListingsQuery => ({
  make: filterMake.value || undefined,
  model: filterModel.value || undefined,
  year_min: filterYearMin.value ? Number(filterYearMin.value) : undefined,
  year_max: filterYearMax.value ? Number(filterYearMax.value) : undefined,
  // price_min/max in UI are whole euros; multiply to cents for API
  price_min: filterPriceMin.value ? Number(filterPriceMin.value) * 100 : undefined,
  price_max: filterPriceMax.value ? Number(filterPriceMax.value) * 100 : undefined,
  fuel: (filterFuel.value as FuelType) || undefined,
  body: (filterBody.value as BodyType) || undefined,
  transmission: (filterTransmission.value as TransmissionType) || undefined,
  location: filterLocation.value || undefined,
  limit: PAGE_SIZE,
  offset: (currentPage.value - 1) * PAGE_SIZE,
}))

const { data, pending, error } = useListings(apiQuery)

const totalPages = computed(() => Math.ceil((data.value?.total ?? 0) / PAGE_SIZE))
const hasResults = computed(() => (data.value?.items.length ?? 0) > 0)

// ---------------------------------------------------------------------------
// Sync filters to URL
// ---------------------------------------------------------------------------
function applyFilters() {
  currentPage.value = 1
  pushQuery()
}

function pushQuery() {
  router.push({
    query: {
      ...(filterMake.value && { make: filterMake.value }),
      ...(filterModel.value && { model: filterModel.value }),
      ...(filterYearMin.value && { year_min: filterYearMin.value }),
      ...(filterYearMax.value && { year_max: filterYearMax.value }),
      ...(filterPriceMin.value && { price_min: filterPriceMin.value }),
      ...(filterPriceMax.value && { price_max: filterPriceMax.value }),
      ...(filterFuel.value && { fuel: filterFuel.value }),
      ...(filterBody.value && { body: filterBody.value }),
      ...(filterTransmission.value && { transmission: filterTransmission.value }),
      ...(filterLocation.value && { location: filterLocation.value }),
      ...(currentPage.value > 1 && { page: String(currentPage.value) }),
    },
  })
}

function clearFilters() {
  filterMake.value = ''
  filterModel.value = ''
  filterYearMin.value = ''
  filterYearMax.value = ''
  filterPriceMin.value = ''
  filterPriceMax.value = ''
  filterFuel.value = ''
  filterBody.value = ''
  filterTransmission.value = ''
  filterLocation.value = ''
  currentPage.value = 1
  router.push({ query: {} })
}

function goToPage(page: number) {
  currentPage.value = page
  pushQuery()
  if (import.meta.client) window.scrollTo({ top: 0, behavior: 'smooth' })
}

// Active filter count for badge
const activeFilterCount = computed(
  () =>
    [
      filterMake.value,
      filterModel.value,
      filterYearMin.value,
      filterYearMax.value,
      filterPriceMin.value,
      filterPriceMax.value,
      filterFuel.value,
      filterBody.value,
      filterTransmission.value,
      filterLocation.value,
    ].filter(Boolean).length,
)

// ---------------------------------------------------------------------------
// Select options
// ---------------------------------------------------------------------------
// Values MUST match the backend enums in src/auto48/models/vehicle.py.
const fuelOptions = [
  { value: 'petrol', label: 'Petrol' },
  { value: 'diesel', label: 'Diesel' },
  { value: 'electric', label: 'Electric' },
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'plugin_hybrid', label: 'Plug-in hybrid' },
  { value: 'lpg', label: 'LPG' },
  { value: 'cng', label: 'CNG' },
  { value: 'other', label: 'Other' },
]

const bodyOptions = [
  { value: 'sedan', label: 'Sedan' },
  { value: 'hatchback', label: 'Hatchback' },
  { value: 'wagon', label: 'Wagon / Estate' },
  { value: 'suv', label: 'SUV / Crossover' },
  { value: 'coupe', label: 'Coupé' },
  { value: 'convertible', label: 'Convertible' },
  { value: 'minivan', label: 'Minivan' },
  { value: 'pickup', label: 'Pickup' },
  { value: 'van', label: 'Van' },
  { value: 'other', label: 'Other' },
]

const transmissionOptions = [
  { value: 'manual', label: 'Manual' },
  { value: 'automatic', label: 'Automatic' },
  { value: 'semi_automatic', label: 'Semi-auto' },
  { value: 'cvt', label: 'CVT' },
]

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 35 }, (_, i) => currentYear - i)
</script>

<template>
  <main class="browse-page">
    <!-- Filter bar -->
    <aside class="filter-sidebar" aria-label="Search filters">
      <div class="filter-sidebar__header">
        <h2 class="filter-sidebar__title">Filters</h2>
        <button
          v-if="activeFilterCount > 0"
          class="filter-sidebar__clear"
          type="button"
          @click="clearFilters"
        >
          Clear all
          <span class="filter-badge">{{ activeFilterCount }}</span>
        </button>
      </div>

      <form class="filter-form" @submit.prevent="applyFilters">
        <fieldset class="filter-group">
          <legend class="filter-group__legend">Make & model</legend>
          <input
            v-model="filterMake"
            class="filter-input"
            type="text"
            placeholder="Make (e.g. Toyota)"
            aria-label="Make"
          />
          <input
            v-model="filterModel"
            class="filter-input"
            type="text"
            placeholder="Model (e.g. Corolla)"
            aria-label="Model"
          />
        </fieldset>

        <fieldset class="filter-group">
          <legend class="filter-group__legend">Year</legend>
          <div class="filter-row">
            <select v-model="filterYearMin" class="filter-select" aria-label="Year from">
              <option value="">From</option>
              <option v-for="y in yearOptions" :key="y" :value="String(y)">{{ y }}</option>
            </select>
            <select v-model="filterYearMax" class="filter-select" aria-label="Year to">
              <option value="">To</option>
              <option v-for="y in yearOptions" :key="y" :value="String(y)">{{ y }}</option>
            </select>
          </div>
        </fieldset>

        <fieldset class="filter-group">
          <legend class="filter-group__legend">Price (€)</legend>
          <div class="filter-row">
            <input
              v-model="filterPriceMin"
              class="filter-input"
              type="number"
              min="0"
              placeholder="Min"
              aria-label="Min price in euros"
            />
            <input
              v-model="filterPriceMax"
              class="filter-input"
              type="number"
              min="0"
              placeholder="Max"
              aria-label="Max price in euros"
            />
          </div>
        </fieldset>

        <fieldset class="filter-group">
          <legend class="filter-group__legend">Fuel type</legend>
          <select v-model="filterFuel" class="filter-select" aria-label="Fuel type">
            <option value="">Any fuel</option>
            <option v-for="opt in fuelOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </fieldset>

        <fieldset class="filter-group">
          <legend class="filter-group__legend">Body type</legend>
          <select v-model="filterBody" class="filter-select" aria-label="Body type">
            <option value="">Any body</option>
            <option v-for="opt in bodyOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </fieldset>

        <fieldset class="filter-group">
          <legend class="filter-group__legend">Transmission</legend>
          <select v-model="filterTransmission" class="filter-select" aria-label="Transmission">
            <option value="">Any</option>
            <option v-for="opt in transmissionOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </fieldset>

        <fieldset class="filter-group">
          <legend class="filter-group__legend">Location</legend>
          <input
            v-model="filterLocation"
            class="filter-input"
            type="text"
            placeholder="City or county"
            aria-label="Location"
          />
        </fieldset>

        <button type="submit" class="btn btn--primary btn--full">
          Search
        </button>
      </form>
    </aside>

    <!-- Results area -->
    <section class="results-area" aria-label="Listing results" aria-live="polite">
      <div class="results-header">
        <p class="results-count">
          <template v-if="!pending && !error">
            <strong>{{ data?.total ?? 0 }}</strong> cars found
          </template>
          <template v-else-if="pending">Searching…</template>
        </p>
      </div>

      <!-- Loading skeleton -->
      <div v-if="pending" class="results-grid">
        <div v-for="n in 8" :key="n" class="listing-card listing-card--skeleton" aria-hidden="true">
          <div class="listing-card__photo skeleton-block" />
          <div class="listing-card__body">
            <div class="skeleton-line skeleton-line--wide" />
            <div class="skeleton-line skeleton-line--narrow" />
            <div class="skeleton-line skeleton-line--mid" />
          </div>
        </div>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="state-message state-message--error" role="alert">
        <p class="state-message__title">Could not load listings</p>
        <p class="state-message__body">The API is unreachable. Start the backend and try again.</p>
      </div>

      <!-- Empty state -->
      <div v-else-if="!hasResults" class="state-message">
        <p class="state-message__title">No cars match your filters</p>
        <p class="state-message__body">Try broadening your search or <button type="button" class="link-btn" @click="clearFilters">clear all filters</button>.</p>
      </div>

      <!-- Results grid -->
      <div v-else class="results-grid">
        <NuxtLink
          v-for="listing in data?.items"
          :key="listing.id"
          :to="`/listings/${listing.id}`"
          class="listing-card"
          :aria-label="`${listing.title}, ${formatEur(listing.price_eur)}`"
        >
          <div class="listing-card__photo">
            <img
              v-if="listing.thumbnail_url"
              :src="listing.thumbnail_url"
              :alt="`${listing.make} ${listing.model} ${listing.year}`"
              loading="lazy"
              class="listing-card__img"
            />
            <div v-else class="listing-card__no-photo" aria-hidden="true">No photo</div>
            <span v-if="listing.status === 'sold'" class="listing-card__sold-badge">Sold</span>
          </div>

          <div class="listing-card__body">
            <h3 class="listing-card__title">{{ listing.title }}</h3>
            <p class="listing-card__price">{{ formatEur(listing.price_eur) }}</p>
            <div class="listing-card__meta">
              <span>{{ listing.year }}</span>
              <span class="meta-dot" aria-hidden="true">·</span>
              <span>{{ formatMileage(listing.mileage_km) }}</span>
              <span class="meta-dot" aria-hidden="true">·</span>
              <span>{{ listing.fuel }}</span>
            </div>
            <p class="listing-card__location">{{ listing.location }}</p>
          </div>
        </NuxtLink>
      </div>

      <!-- Pagination -->
      <nav
        v-if="totalPages > 1"
        class="pagination"
        aria-label="Pagination"
      >
        <button
          class="pagination__btn"
          type="button"
          :disabled="currentPage <= 1"
          aria-label="Previous page"
          @click="goToPage(currentPage - 1)"
        >
          &larr; Prev
        </button>
        <span class="pagination__info">{{ currentPage }} / {{ totalPages }}</span>
        <button
          class="pagination__btn"
          type="button"
          :disabled="currentPage >= totalPages"
          aria-label="Next page"
          @click="goToPage(currentPage + 1)"
        >
          Next &rarr;
        </button>
      </nav>
    </section>
  </main>
</template>

<style scoped>
/* ---- Layout ---- */
.browse-page {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem 1.25rem 3rem;
  align-items: start;
  font-family: system-ui, sans-serif;
}

@media (max-width: 768px) {
  .browse-page {
    grid-template-columns: 1fr;
  }
}

/* ---- Filter sidebar ---- */
.filter-sidebar {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 1.25rem;
  position: sticky;
  top: 76px;
}

.filter-sidebar__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.filter-sidebar__title {
  font-size: 1rem;
  font-weight: 700;
  color: #111;
  margin: 0;
}

.filter-sidebar__clear {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.8rem;
  color: #6b7280;
  padding: 0;
}

.filter-sidebar__clear:hover { color: #dc2626; }

.filter-badge {
  background: #2563eb;
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
  border-radius: 999px;
  padding: 0 0.4em;
  min-width: 1.25em;
  text-align: center;
}

.filter-form { display: flex; flex-direction: column; gap: 1rem; }

.filter-group {
  border: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.filter-group__legend {
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6b7280;
  margin-bottom: 0.15rem;
}

.filter-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}

.filter-input,
.filter-select {
  width: 100%;
  padding: 0.5rem 0.65rem;
  border: 1px solid #d1d5db;
  border-radius: 7px;
  font-size: 0.875rem;
  font-family: inherit;
  color: #111;
  background: #fafafa;
  transition: border-color 0.15s, box-shadow 0.15s;
  box-sizing: border-box;
}

.filter-input:focus,
.filter-select:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgb(37 99 235 / 12%);
  background: #fff;
}

/* ---- Buttons ---- */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  border: none;
  text-decoration: none;
  transition: background 0.15s, box-shadow 0.15s;
  font-family: inherit;
}
.btn--primary { background: #2563eb; color: #fff; padding: 0.6rem 1.2rem; font-size: 0.9rem; }
.btn--primary:hover { background: #1d4ed8; box-shadow: 0 2px 8px rgb(37 99 235 / 30%); }
.btn--full { width: 100%; }

.link-btn {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  font-size: inherit;
  padding: 0;
  text-decoration: underline;
}

/* ---- Results header ---- */
.results-header { margin-bottom: 1rem; }
.results-count { font-size: 0.9rem; color: #374151; margin: 0; }
.results-count strong { color: #111; }

/* ---- Listing cards grid ---- */
.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1.25rem;
}

.listing-card {
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  transition: box-shadow 0.18s, transform 0.18s;
}

.listing-card:hover {
  box-shadow: 0 4px 16px rgb(0 0 0 / 10%);
  transform: translateY(-2px);
}

.listing-card__photo {
  position: relative;
  aspect-ratio: 4 / 3;
  background: #f3f4f6;
}

.listing-card__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.listing-card__no-photo {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  font-size: 0.8rem;
  color: #9ca3af;
}

.listing-card__sold-badge {
  position: absolute;
  top: 0.5rem;
  left: 0.5rem;
  background: rgb(0 0 0 / 65%);
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.2em 0.55em;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.listing-card__body {
  padding: 0.875rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  flex: 1;
}

.listing-card__title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #111;
  margin: 0;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.listing-card__price {
  font-size: 1.05rem;
  font-weight: 700;
  color: #2563eb;
  margin: 0.1rem 0 0;
}

.listing-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.2rem 0.4rem;
  font-size: 0.78rem;
  color: #6b7280;
  margin-top: 0.2rem;
}

.meta-dot { color: #d1d5db; }

.listing-card__location {
  font-size: 0.78rem;
  color: #9ca3af;
  margin: 0;
  margin-top: auto;
  padding-top: 0.35rem;
}

/* ---- Skeleton ---- */
.listing-card--skeleton { pointer-events: none; }

@keyframes shimmer {
  0%   { background-position: -400px 0; }
  100% { background-position: 400px 0; }
}

.skeleton-block,
.skeleton-line {
  background: linear-gradient(90deg, #f0f0f0 25%, #e8e8e8 50%, #f0f0f0 75%);
  background-size: 800px 100%;
  animation: shimmer 1.4s infinite linear;
  border-radius: 4px;
}

.skeleton-block { width: 100%; height: 100%; }
.skeleton-line { height: 0.85rem; }
.skeleton-line--wide   { width: 80%; }
.skeleton-line--mid    { width: 60%; }
.skeleton-line--narrow { width: 40%; }

/* ---- State messages ---- */
.state-message {
  padding: 3rem 1.5rem;
  text-align: center;
  border: 1px dashed #e5e7eb;
  border-radius: 12px;
  background: #fafafa;
}

.state-message--error { border-color: #fca5a5; background: #fff5f5; }

.state-message__title {
  font-size: 1.05rem;
  font-weight: 600;
  color: #374151;
  margin: 0 0 0.35rem;
}

.state-message__body {
  font-size: 0.9rem;
  color: #6b7280;
  margin: 0;
}

/* ---- Pagination ---- */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 2rem;
}

.pagination__btn {
  padding: 0.5rem 1.1rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 0.875rem;
  font-family: inherit;
  color: #374151;
  transition: background 0.15s, border-color 0.15s;
}

.pagination__btn:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.pagination__btn:disabled { opacity: 0.4; cursor: default; }

.pagination__info {
  font-size: 0.875rem;
  color: #6b7280;
  min-width: 4rem;
  text-align: center;
}
</style>
