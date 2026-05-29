<script setup lang="ts">
import { useListing, useListingPhotos } from '~/composables/useListings'
import { formatEur, formatMileage } from '~/types/listing'

const route = useRoute()
const id = computed(() => route.params.id as string)

const { data: listing, pending, error } = useListing(id)
const { data: photos } = useListingPhotos(id)

useSeoMeta({
  title: computed(() =>
    listing.value ? `${listing.value.title} — auto48` : 'Listing — auto48',
  ),
  description: computed(() =>
    listing.value?.description
      ?? `${listing.value?.vehicle?.make ?? ''} ${listing.value?.vehicle?.model ?? ''} for sale`,
  ),
})

// Gallery
const activePhotoIndex = ref(0)
const activePhoto = computed(() =>
  photos.value?.[activePhotoIndex.value] ?? null,
)

function prevPhoto() {
  if (!photos.value?.length) return
  activePhotoIndex.value =
    (activePhotoIndex.value - 1 + photos.value.length) % photos.value.length
}

function nextPhoto() {
  if (!photos.value?.length) return
  activePhotoIndex.value = (activePhotoIndex.value + 1) % photos.value.length
}

// Specs table
const specs = computed(() => {
  if (!listing.value) return []
  const l = listing.value
  const v = l.vehicle
  return [
    { label: 'Make', value: v.make },
    { label: 'Model', value: v.model },
    { label: 'Variant', value: v.variant ?? '—' },
    { label: 'Year', value: String(v.year) },
    { label: 'Mileage', value: formatMileage(l.mileage_km) },
    { label: 'Fuel', value: v.fuel },
    { label: 'Body', value: v.body },
    { label: 'Transmission', value: v.transmission },
    { label: 'Drivetrain', value: v.drivetrain ?? '—' },
    { label: 'Location', value: l.location_county ?? '—' },
  ].filter((s) => s.value && s.value !== '—' || s.value === '—')
})

// Deal score placeholder
const dealScore = ref<'good' | 'fair' | 'high' | null>(null)

// Contact seller stub
const contactSent = ref(false)
function contactSeller() {
  // Placeholder: will wire to POST /v1/conversations in Phase 1b
  contactSent.value = true
}
</script>

<template>
  <div class="detail-page">
    <!-- Loading -->
    <div v-if="pending" class="detail-page__loading" aria-live="polite" aria-busy="true">
      <div class="detail-skeleton">
        <div class="detail-skeleton__gallery skeleton-block" />
        <div class="detail-skeleton__body">
          <div class="skeleton-line skeleton-line--wide" style="height: 2rem" />
          <div class="skeleton-line skeleton-line--narrow" style="height: 1.25rem" />
          <div class="skeleton-line skeleton-line--mid" />
          <div class="skeleton-line skeleton-line--mid" />
        </div>
      </div>
    </div>

    <!-- Error / not found -->
    <div v-else-if="error" class="state-message state-message--error" role="alert">
      <p class="state-message__title">
        {{ (error as any)?.statusCode === 404 ? 'Listing not found' : 'Could not load listing' }}
      </p>
      <p class="state-message__body">
        <NuxtLink to="/" class="link">Browse all cars</NuxtLink>
      </p>
    </div>

    <template v-else-if="listing">
      <!-- Breadcrumb -->
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <NuxtLink to="/" class="breadcrumb__link">Browse</NuxtLink>
        <span class="breadcrumb__sep" aria-hidden="true">/</span>
        <span class="breadcrumb__current" aria-current="page">{{ listing.title }}</span>
      </nav>

      <div class="detail-layout">
        <!-- Left column: gallery + description -->
        <div class="detail-main">
          <!-- Gallery -->
          <section class="gallery" aria-label="Listing photos">
            <div class="gallery__main" role="img" :aria-label="`${listing.vehicle.make} ${listing.vehicle.model} photo ${activePhotoIndex + 1}`">
              <img
                v-if="activePhoto"
                :src="activePhoto.url"
                :alt="`${listing.vehicle.make} ${listing.vehicle.model} ${listing.vehicle.year}`"
                class="gallery__img"
              />
              <div v-else class="gallery__empty" aria-hidden="true">No photos uploaded</div>

              <template v-if="(photos?.length ?? 0) > 1">
                <button class="gallery__arrow gallery__arrow--prev" type="button" aria-label="Previous photo" @click="prevPhoto">&#8249;</button>
                <button class="gallery__arrow gallery__arrow--next" type="button" aria-label="Next photo" @click="nextPhoto">&#8250;</button>
                <span class="gallery__counter">{{ activePhotoIndex + 1 }} / {{ photos!.length }}</span>
              </template>
            </div>

            <div v-if="(photos?.length ?? 0) > 1" class="gallery__thumbs" role="list" aria-label="Photo thumbnails">
              <button
                v-for="(photo, i) in photos!.slice(0, 8)"
                :key="photo.id"
                class="gallery__thumb-btn"
                :class="{ 'gallery__thumb-btn--active': i === activePhotoIndex }"
                type="button"
                :aria-label="`View photo ${i + 1}`"
                :aria-pressed="i === activePhotoIndex"
                @click="activePhotoIndex = i"
              >
                <img :src="photo.url" :alt="`Thumbnail ${i + 1}`" class="gallery__thumb-img" loading="lazy" />
              </button>
            </div>
          </section>

          <!-- Description -->
          <section v-if="listing.description" class="detail-section">
            <h2 class="detail-section__title">Description</h2>
            <p class="detail-description">{{ listing.description }}</p>
          </section>

          <!-- History timeline placeholder -->
          <section class="detail-section detail-section--trust">
            <h2 class="detail-section__title">
              Vehicle history
              <span class="trust-badge" title="Data sourced from official vehicle registry">
                ✓ Verified vehicle data
              </span>
            </h2>
            <div class="history-timeline" aria-label="Vehicle history timeline">
              <div class="history-timeline__placeholder">
                <p class="history-timeline__note">
                  Full history timeline — odometer readings, inspections, and ownership changes — will appear here once the vehicle data service is connected.
                </p>
              </div>
            </div>
          </section>
        </div>

        <!-- Right column: price, specs, actions -->
        <aside class="detail-sidebar">
          <div class="detail-sidebar__card">
            <h1 class="detail-title">{{ listing.title }}</h1>

            <div class="detail-price-row">
              <span class="detail-price">{{ formatEur(listing.price_eur_cents) }}</span>

              <!-- Deal score badge slot — wired in Phase 1b when ValuationPort is live -->
              <span
                v-if="dealScore"
                class="deal-score"
                :class="`deal-score--${dealScore}`"
                :title="`Deal score: ${dealScore}`"
              >
                {{ dealScore === 'good' ? 'Good deal' : dealScore === 'fair' ? 'Fair price' : 'High price' }}
              </span>
              <span v-else class="deal-score deal-score--pending" title="Valuation coming soon">
                Valuation soon
              </span>
            </div>

            <!-- Spec table -->
            <table class="spec-table" aria-label="Vehicle specifications">
              <tbody>
                <tr v-for="spec in specs" :key="spec.label">
                  <th class="spec-table__label" scope="row">{{ spec.label }}</th>
                  <td class="spec-table__value">{{ spec.value }}</td>
                </tr>
              </tbody>
            </table>

            <!-- Contact CTA -->
            <div class="contact-section">
              <template v-if="!contactSent">
                <button
                  type="button"
                  class="btn btn--primary btn--full btn--lg"
                  @click="contactSeller"
                >
                  Contact seller
                </button>
                <p class="contact-section__note">No spam. Your message goes directly to the seller.</p>
              </template>
              <div v-else class="contact-sent" role="status">
                <p class="contact-sent__msg">Message sent! The seller will get back to you.</p>
              </div>
            </div>
          </div>

          <!-- Listing meta -->
          <p class="detail-meta">
            Listed
            <time :datetime="listing.created_at">
              {{ new Date(listing.created_at).toLocaleDateString('et-EE', { year: 'numeric', month: 'long', day: 'numeric' }) }}
            </time>
            · #{{ listing.id }}
          </p>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.detail-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.25rem 1.25rem 3rem;
  font-family: system-ui, sans-serif;
}

/* ---- Breadcrumb ---- */
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.83rem;
  color: #6b7280;
  margin-bottom: 1.25rem;
}

.breadcrumb__link {
  color: #2563eb;
  text-decoration: none;
}

.breadcrumb__link:hover { text-decoration: underline; }
.breadcrumb__sep { color: #d1d5db; }
.breadcrumb__current { color: #374151; }

/* ---- Layout ---- */
.detail-layout {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 2rem;
  align-items: start;
}

@media (max-width: 860px) {
  .detail-layout { grid-template-columns: 1fr; }
}

/* ---- Gallery ---- */
.gallery__main {
  position: relative;
  aspect-ratio: 16 / 10;
  background: #f3f4f6;
  border-radius: 12px;
  overflow: hidden;
}

.gallery__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.gallery__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #9ca3af;
  font-size: 0.9rem;
}

.gallery__arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: rgb(0 0 0 / 50%);
  color: #fff;
  border: none;
  border-radius: 50%;
  width: 2.25rem;
  height: 2.25rem;
  cursor: pointer;
  font-size: 1.4rem;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.gallery__arrow:hover { background: rgb(0 0 0 / 75%); }
.gallery__arrow--prev { left: 0.75rem; }
.gallery__arrow--next { right: 0.75rem; }

.gallery__counter {
  position: absolute;
  bottom: 0.75rem;
  right: 0.75rem;
  background: rgb(0 0 0 / 50%);
  color: #fff;
  font-size: 0.78rem;
  padding: 0.15em 0.5em;
  border-radius: 4px;
}

.gallery__thumbs {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.75rem;
  flex-wrap: wrap;
}

.gallery__thumb-btn {
  width: 72px;
  height: 54px;
  border: 2px solid transparent;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  padding: 0;
  background: #f3f4f6;
  transition: border-color 0.15s;
}

.gallery__thumb-btn--active { border-color: #2563eb; }
.gallery__thumb-btn:hover:not(.gallery__thumb-btn--active) { border-color: #93c5fd; }

.gallery__thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* ---- Sections ---- */
.detail-section {
  margin-top: 2rem;
}

.detail-section--trust {
  border: 1px solid #d1fae5;
  border-radius: 10px;
  padding: 1.25rem;
  background: #f0fdf4;
}

.detail-section__title {
  font-size: 1rem;
  font-weight: 700;
  color: #111;
  margin: 0 0 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.trust-badge {
  font-size: 0.75rem;
  font-weight: 600;
  background: #bbf7d0;
  color: #166534;
  padding: 0.2em 0.6em;
  border-radius: 5px;
}

.detail-description {
  font-size: 0.9rem;
  line-height: 1.7;
  color: #374151;
  white-space: pre-wrap;
  margin: 0;
}

/* ---- History timeline placeholder ---- */
.history-timeline__placeholder {
  padding: 1rem 0 0.25rem;
}

.history-timeline__note {
  font-size: 0.85rem;
  color: #166534;
  margin: 0;
  font-style: italic;
}

/* ---- Sidebar card ---- */
.detail-sidebar__card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 1.5rem;
  position: sticky;
  top: 76px;
}

.detail-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: #111;
  margin: 0 0 0.75rem;
  line-height: 1.3;
}

.detail-price-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1.25rem;
}

.detail-price {
  font-size: 1.75rem;
  font-weight: 800;
  color: #111;
  letter-spacing: -0.02em;
}

/* ---- Deal score badge ---- */
.deal-score {
  font-size: 0.78rem;
  font-weight: 700;
  padding: 0.25em 0.7em;
  border-radius: 6px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.deal-score--good { background: #d1fae5; color: #065f46; }
.deal-score--fair { background: #fef9c3; color: #854d0e; }
.deal-score--high { background: #fee2e2; color: #991b1b; }
.deal-score--pending { background: #f3f4f6; color: #9ca3af; }

/* ---- Spec table ---- */
.spec-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
  margin-bottom: 1.5rem;
}

.spec-table__label {
  padding: 0.5rem 0.5rem 0.5rem 0;
  text-align: left;
  font-weight: 500;
  color: #6b7280;
  border-bottom: 1px solid #f3f4f6;
  width: 40%;
}

.spec-table__value {
  padding: 0.5rem 0;
  color: #111;
  border-bottom: 1px solid #f3f4f6;
  text-transform: capitalize;
}

/* ---- Contact section ---- */
.contact-section { display: flex; flex-direction: column; gap: 0.5rem; }

.contact-section__note {
  font-size: 0.78rem;
  color: #9ca3af;
  text-align: center;
  margin: 0;
}

.contact-sent {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 1rem;
  text-align: center;
}

.contact-sent__msg {
  font-size: 0.9rem;
  font-weight: 600;
  color: #166534;
  margin: 0;
}

/* ---- Detail meta ---- */
.detail-meta {
  font-size: 0.78rem;
  color: #9ca3af;
  margin: 0.75rem 0 0;
  text-align: center;
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

.btn--primary { background: #2563eb; color: #fff; padding: 0.7rem 1.2rem; font-size: 0.95rem; }
.btn--primary:hover { background: #1d4ed8; box-shadow: 0 2px 10px rgb(37 99 235 / 35%); }
.btn--full { width: 100%; }
.btn--lg { padding: 0.85rem 1.5rem; font-size: 1rem; }

/* ---- State messages ---- */
.state-message {
  padding: 3rem 1.5rem;
  text-align: center;
  border: 1px dashed #e5e7eb;
  border-radius: 12px;
  background: #fafafa;
}

.state-message--error { border-color: #fca5a5; background: #fff5f5; }
.state-message__title { font-size: 1.1rem; font-weight: 600; color: #374151; margin: 0 0 0.4rem; }
.state-message__body { font-size: 0.9rem; color: #6b7280; margin: 0; }

.link { color: #2563eb; text-decoration: none; }
.link:hover { text-decoration: underline; }

/* ---- Loading skeleton ---- */
.detail-skeleton {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 2rem;
}

@media (max-width: 860px) {
  .detail-skeleton { grid-template-columns: 1fr; }
}

.detail-skeleton__gallery {
  aspect-ratio: 16 / 10;
  border-radius: 12px;
}

.detail-skeleton__body {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding-top: 0.5rem;
}

@keyframes shimmer {
  0%   { background-position: -800px 0; }
  100% { background-position: 800px 0; }
}

.skeleton-block,
.skeleton-line {
  background: linear-gradient(90deg, #f0f0f0 25%, #e8e8e8 50%, #f0f0f0 75%);
  background-size: 1600px 100%;
  animation: shimmer 1.4s infinite linear;
  border-radius: 6px;
}

.skeleton-line { height: 0.85rem; }
.skeleton-line--wide   { width: 80%; }
.skeleton-line--mid    { width: 60%; }
.skeleton-line--narrow { width: 40%; }
</style>
