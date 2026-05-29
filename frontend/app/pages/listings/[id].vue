<script setup lang="ts">
import { useListing, useListingPhotos, useListings } from '~/composables/useListings'
import { formatEur, formatMileage } from '~/types/listing'
import type { ListingsQuery } from '~/types/listing'
import type { ValuationParams } from '~/composables/useValuation'

const route = useRoute()
const id = computed(() => route.params.id as string)

const { data: listing, pending, error } = useListing(id)
const { data: photos } = useListingPhotos(id)

useSeoMeta({
  title: computed(() => (listing.value ? `${listing.value.title} — auto48` : 'Kuulutus — auto48')),
  description: computed(() =>
    listing.value?.description
    ?? `${listing.value?.vehicle?.make ?? ''} ${listing.value?.vehicle?.model ?? ''} müügis auto48-s`,
  ),
})

// ---- valuation (real fairness) ----
const valParams = computed<ValuationParams | null>(() => {
  const l = listing.value
  if (!l) return null
  return {
    make: l.vehicle.make,
    model: l.vehicle.model,
    year: l.vehicle.year,
    mileage_km: l.mileage_km ?? undefined,
    price_eur_cents: l.price_eur_cents,
  }
})
const { data: valuation, fairness } = useValuation(valParams)

const fairDetail = computed(() => {
  const f = fairness.value
  const market = valuation.value.estimate_eur_cents
  if (f.key === 'great' || f.key === 'good') {
    return f.pct != null && market != null
      ? `${f.pct}% alla turuhinna (${formatEur(market)})`
      : 'Hind on alla turuhinna'
  }
  if (f.key === 'high') {
    return f.pct != null ? `${f.pct}% üle turuhinna` : 'Hind on üle turuhinna'
  }
  if (f.key === 'fair') {
    return market != null ? `Vastab turuhinnale (${formatEur(market)})` : 'Vastab turuhinnale'
  }
  return 'Turuhinda ei saa veel arvutada'
})

// ---- financing ----
const monthly = computed(() => (listing.value ? monthlyEstimateCents(listing.value.price_eur_cents) : 0))

// ---- gallery ----
const activePhoto = ref(0)
const photoList = computed(() => photos.value ?? [])
const mainPhotoUrl = computed(() => photoList.value[activePhoto.value]?.url ?? null)
const saved = ref(false)
watch(id, () => { activePhoto.value = 0 })

// ---- specs (real data only) ----
const specs = computed(() => {
  const l = listing.value
  if (!l) return []
  const v = l.vehicle
  const s = (v.specs ?? {}) as Record<string, unknown>
  const out: { ic: string, label: string, val: string }[] = [
    { ic: 'calendar', label: 'Esmane registreerimine', val: String(v.year) },
    { ic: 'gauge', label: 'Läbisõit', val: formatMileage(l.mileage_km) },
    { ic: fuelIcon[v.fuel], label: 'Kütus', val: fuelLabel[v.fuel] },
    { ic: 'cog', label: 'Käigukast', val: transmissionLabel[v.transmission] },
    { ic: 'car', label: 'Keretüüp', val: bodyLabel[v.body] },
  ]
  if (v.drivetrain) out.push({ ic: 'git-fork', label: 'Vedu', val: drivetrainLabel[v.drivetrain] })
  if (v.variant) out.push({ ic: 'tag', label: 'Varustustase', val: v.variant })
  // Optional extras if present in the freeform specs object.
  if (typeof s.power_kw === 'number') out.push({ ic: 'zap', label: 'Võimsus', val: `${s.power_kw} kW` })
  if (typeof s.engine_cc === 'number') out.push({ ic: 'gauge-circle', label: 'Töömaht', val: `${s.engine_cc} cm³` })
  if (typeof s.color === 'string') out.push({ ic: 'palette', label: 'Värv', val: s.color })
  if (l.location_county) out.push({ ic: 'map-pin', label: 'Asukoht', val: l.location_county })
  return out
})

// Optional equipment list from specs.features.
const features = computed(() => {
  const f = (listing.value?.vehicle.specs as Record<string, unknown> | undefined)?.features
  return Array.isArray(f) ? (f as string[]) : []
})

// ---- similar listings ----
const similarQuery = computed<ListingsQuery>(() => ({
  body: listing.value?.vehicle.body,
  limit: 5,
  sort: 'newest',
}))
const { data: similarData } = useListings(similarQuery)
const similar = computed(() =>
  (similarData.value?.items ?? []).filter(c => c.id !== listing.value?.id).slice(0, 4),
)

// ---- contact (stub until conversations are wired) ----
const phoneRevealed = ref(false)
const messageSent = ref(false)
</script>

<template>
  <div>
    <LightNav />

    <!-- loading -->
    <div v-if="pending && !listing" class="state-msg">
      <h2>Laen kuulutust…</h2>
    </div>

    <!-- error -->
    <div v-else-if="error || !listing" class="state-msg err">
      <h2>{{ (error as any)?.statusCode === 404 ? 'Kuulutust ei leitud' : 'Kuulutuse laadimine ebaõnnestus' }}</h2>
      <p><NuxtLink to="/search" class="link">Sirvi kõiki autosid</NuxtLink></p>
    </div>

    <template v-else>
      <nav class="breadcrumb" aria-label="Murenavigatsioon">
        <NuxtLink to="/search"><Icon name="arrow-left" :size="15" />Tagasi otsingusse</NuxtLink>
        <span class="bc-sep">/</span>
        <span>{{ bodyLabel[listing.vehicle.body] }}</span>
        <span class="bc-sep">/</span>
        <span class="bc-cur">{{ listing.vehicle.make }} {{ listing.vehicle.model }}</span>
      </nav>

      <div class="detail-layout">
        <div class="detail-main">
          <!-- gallery -->
          <div class="gallery">
            <div class="g-main">
              <CarPhoto :url="mainPhotoUrl" :seed="listing.id" big :alt="`${listing.vehicle.make} ${listing.vehicle.model}`" />
              <button
                type="button"
                class="g-save"
                :class="{ on: saved }"
                :aria-pressed="saved"
                aria-label="Salvesta"
                @click="saved = !saved"
              >
                <Icon name="heart" :size="18" />
              </button>
              <span v-if="photoList.length" class="g-count mono">
                <Icon name="image" :size="13" />{{ activePhoto + 1 }} / {{ photoList.length }}
              </span>
            </div>

            <div v-if="photoList.length > 1" class="g-thumbs">
              <button
                v-for="(p, i) in photoList.slice(0, 6)"
                :key="p.id"
                type="button"
                class="g-thumb"
                :class="{ on: i === activePhoto }"
                :aria-label="`Foto ${i + 1}`"
                @click="activePhoto = i"
              >
                <img :src="p.url" :alt="`Pisipilt ${i + 1}`" loading="lazy">
              </button>
              <button v-if="photoList.length > 6" type="button" class="g-thumb more">+{{ photoList.length - 6 }}</button>
            </div>
          </div>

          <!-- description -->
          <div v-if="listing.description" class="d-card">
            <h2>Kirjeldus</h2>
            <p class="d-desc">{{ listing.description }}</p>
          </div>

          <!-- technical specs -->
          <div class="d-card">
            <h2>Tehnilised andmed</h2>
            <div class="spec-grid">
              <div v-for="s in specs" :key="s.label" class="spec-item">
                <Icon :name="s.ic" :size="17" class="si" />
                <div>
                  <div class="sl">{{ s.label }}</div>
                  <div class="sv">{{ s.val }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- trust / background check (honest placeholder until data service is live) -->
          <div class="d-card trust-card">
            <div class="trust-head">
              <div class="th-ic"><Icon name="shield-check" :size="22" /></div>
              <div>
                <h2 style="margin: 0;">Taustakontroll</h2>
                <p class="th-sub">Läbisõit, õnnetuste ajalugu, arestid ja ülevaatus</p>
              </div>
              <span class="th-badge pending"><Icon name="clock" :size="13" />Peagi</span>
            </div>
            <p class="trust-note">
              Auto registriandmetel põhinev taustakontroll — kontrollitud läbisõit, õnnetuste
              ajalugu, arestid ja kehtiv ülevaatus — kuvatakse siin, kui sõidukiandmete teenus
              on ühendatud.
            </p>
          </div>

          <!-- equipment -->
          <div v-if="features.length" class="d-card">
            <h2>Varustus</h2>
            <div class="feat-chips">
              <span v-for="f in features" :key="f" class="feat-chip"><Icon name="check" :size="13" />{{ f }}</span>
            </div>
          </div>
        </div>

        <!-- sticky buy box -->
        <aside class="buybox">
          <div class="bb-card">
            <div class="bb-title">{{ listing.vehicle.make }} {{ listing.vehicle.model }}</div>
            <div class="bb-var">
              <template v-if="listing.vehicle.variant">{{ listing.vehicle.variant }} · </template>{{ listing.vehicle.year }}
            </div>
            <div class="bb-price">{{ formatEur(listing.price_eur_cents) }}</div>

            <div class="bb-fair" :class="fairness.key">
              <Icon :name="fairness.icon" :size="15" />
              <div>
                <b>{{ fairness.label }}</b>
                <span>{{ fairDetail }}</span>
              </div>
            </div>

            <div class="bb-fin">
              <span>Liising alates</span>
              <b class="mono">{{ formatEur(monthly) }}/kuus</b>
            </div>

            <button type="button" class="btn-volt block" @click="phoneRevealed = true">
              <Icon name="phone" :size="16" />{{ phoneRevealed ? '+372 5xx xxx xx' : 'Näita telefoninumbrit' }}
            </button>
            <button type="button" class="btn-dark block" @click="messageSent = true">
              <Icon name="message-square" :size="16" />{{ messageSent ? 'Sõnum saadetud' : 'Saada sõnum' }}
            </button>
            <button type="button" class="btn-ghost block">
              <Icon name="calendar-check" :size="16" />Broneeri proovisõit
            </button>
          </div>

          <div class="bb-seller">
            <div class="bs-ava"><Icon name="user" :size="20" /></div>
            <div class="bs-info">
              <div class="bs-name">Müüja #{{ listing.seller_id }}</div>
              <div class="bs-meta">
                <Icon name="map-pin" :size="13" />{{ listing.location_county ?? 'Asukoht täpsustamisel' }}
              </div>
            </div>
            <Icon name="chevron-right" :size="18" style="color: var(--faint-l);" />
          </div>

          <div class="bb-note">
            <Icon name="shield" :size="14" />
            Kohtu müüjaga avalikus kohas. Ära maksa ettemaksu enne auto nägemist.
          </div>
        </aside>
      </div>

      <!-- similar -->
      <div v-if="similar.length" class="body" style="padding-top: 8px;">
        <div class="sec-head"><div class="ht"><h2>Sarnased autod</h2></div></div>
        <div class="grid">
          <SignalCard v-for="c in similar" :key="c.id" :listing="c" />
        </div>
      </div>

      <DarkFooter />
    </template>
  </div>
</template>
