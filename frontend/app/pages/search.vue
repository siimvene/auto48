<script setup lang="ts">
import { useListings } from '~/composables/useListings'
import type { ListingsQuery, BodyType, FuelType, TransmissionType } from '~/types/listing'

useSeoMeta({
  title: 'Otsing — auto48',
  description: 'Leia sobiv auto auto48 turult. Filtreeri keretüübi, hinna, läbisõidu, kütuse ja käigukasti järgi.',
})

const route = useRoute()
const router = useRouter()

// ---- filter state (initialised from URL) ----
const q = ref<string>((route.query.q as string) ?? '')
const body = ref<BodyType | ''>((route.query.body as BodyType) ?? '')
const fuel = ref<FuelType | ''>((route.query.fuel as FuelType) ?? '')
const transmission = ref<TransmissionType | ''>((route.query.transmission as TransmissionType) ?? '')
const PRICE_MAX = 50000
const KM_MAX = 300000
const priceMax = ref<number>(Number(route.query.price_max_eur ?? PRICE_MAX))
const kmMax = ref<number>(Number(route.query.mileage_max ?? KM_MAX))
const sort = ref<string>((route.query.sort as string) ?? 'newest')

const PAGE_SIZE = 24
const page = ref<number>(Number(route.query.page ?? 1))

// ---- options ----
const fuelOptions: { value: FuelType, label: string }[] = [
  { value: 'diesel', label: 'Diisel' },
  { value: 'petrol', label: 'Bensiin' },
  { value: 'hybrid', label: 'Hübriid' },
  { value: 'plugin_hybrid', label: 'Pistikhübriid' },
  { value: 'electric', label: 'Elektri' },
]
const transmissionOptions: { value: TransmissionType, label: string }[] = [
  { value: 'automatic', label: 'Automaat' },
  { value: 'manual', label: 'Manuaal' },
]
const sortOptions = [
  { id: 'newest', label: 'Uusimad ees' },
  { id: 'price_asc', label: 'Odavaim ees' },
  { id: 'price_desc', label: 'Kallim ees' },
  { id: 'year_desc', label: 'Uuem aasta ees' },
  { id: 'mileage_asc', label: 'Väikseim läbisõit' },
]
const sortOpen = ref(false)
const sortLabel = computed(() => sortOptions.find(s => s.id === sort.value)?.label ?? 'Uusimad ees')

// ---- API query ----
const apiQuery = computed((): ListingsQuery => ({
  q: q.value || undefined,
  body: (body.value as BodyType) || undefined,
  fuel: (fuel.value as FuelType) || undefined,
  transmission: (transmission.value as TransmissionType) || undefined,
  price_max: priceMax.value < PRICE_MAX ? priceMax.value * 100 : undefined,
  mileage_max: kmMax.value < KM_MAX ? kmMax.value : undefined,
  sort: sort.value as ListingsQuery['sort'],
  limit: PAGE_SIZE,
  offset: (page.value - 1) * PAGE_SIZE,
}))

const { data, pending, error } = useListings(apiQuery)
const items = computed(() => data.value?.items ?? [])
const total = computed(() => data.value?.total ?? 0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

// ---- URL sync ----
function pushQuery() {
  router.push({
    query: {
      ...(q.value && { q: q.value }),
      ...(body.value && { body: body.value }),
      ...(fuel.value && { fuel: fuel.value }),
      ...(transmission.value && { transmission: transmission.value }),
      ...(priceMax.value < PRICE_MAX && { price_max_eur: String(priceMax.value) }),
      ...(kmMax.value < KM_MAX && { mileage_max: String(kmMax.value) }),
      ...(sort.value !== 'newest' && { sort: sort.value }),
      ...(page.value > 1 && { page: String(page.value) }),
    },
  })
}

function resetPageAndPush() {
  page.value = 1
  pushQuery()
}

// single-select toggles
function toggleBody(v: BodyType) { body.value = body.value === v ? '' : v; resetPageAndPush() }
function toggleFuel(v: FuelType) { fuel.value = fuel.value === v ? '' : v; resetPageAndPush() }
function toggleTransmission(v: TransmissionType) { transmission.value = transmission.value === v ? '' : v; resetPageAndPush() }
function pickSort(id: string) { sort.value = id; sortOpen.value = false; resetPageAndPush() }

function onSearchSubmit() { resetPageAndPush() }

function clearAll() {
  q.value = ''
  body.value = ''
  fuel.value = ''
  transmission.value = ''
  priceMax.value = PRICE_MAX
  kmMax.value = KM_MAX
  page.value = 1
  router.push({ query: {} })
}

const activeFilters = computed(() =>
  [body.value, fuel.value, transmission.value].filter(Boolean).length
  + (priceMax.value < PRICE_MAX ? 1 : 0)
  + (kmMax.value < KM_MAX ? 1 : 0),
)

function goToPage(p: number) {
  page.value = p
  pushQuery()
  if (import.meta.client) window.scrollTo({ top: 0, behavior: 'smooth' })
}

const fmtEur = (n: number) => n.toLocaleString('et-EE')
const fmtNum = (n: number) => n.toLocaleString('et-EE')
</script>

<template>
  <div>
    <LightNav :query="q" />

    <!-- AI / query banner (honest: free-text server search, no fake NLP) -->
    <div v-if="q" class="ai-banner">
      <div class="ai-left">
        <Icon name="sparkles" :size="18" class="spark" />
        <div>
          <div class="ai-q">„{{ q }}"</div>
          <div class="ai-meta">auto48 otsib seda pealkirjast ning margi-, mudeli- ja varustusandmetest</div>
        </div>
      </div>
      <button type="button" class="ai-toggle btn-ghost" style="margin-left:auto;color:#F3F7EC;border-color:var(--line-d);" @click="q = ''; resetPageAndPush()">
        <Icon name="x" :size="16" />Tühjenda otsing
      </button>
    </div>
    <div v-else class="res-title-bar">
      <h1>Kõik autod</h1>
      <span class="mono">{{ fmtNum(total) }} kuulutust</span>
    </div>

    <div class="results-layout">
      <!-- filter sidebar -->
      <aside class="filters" aria-label="Filtrid">
        <div class="fhead">
          <h3>Filtrid</h3>
          <button v-if="activeFilters > 0" type="button" class="clear" @click="clearAll">Tühjenda ({{ activeFilters }})</button>
        </div>

        <div class="fgroup">
          <h4>Keretüüp</h4>
          <button
            v-for="c in bodyCategories"
            :key="c.id"
            type="button"
            class="fopt"
            :class="{ on: body === c.id }"
            @click="toggleBody(c.id)"
          >
            <span class="box"><Icon :name="body === c.id ? 'check' : 'plus'" :size="12" /></span>
            <span class="flabel">{{ c.label }}</span>
          </button>
        </div>

        <div class="fgroup">
          <h4>Hind kuni</h4>
          <div class="slval mono">{{ fmtEur(priceMax) }}{{ priceMax >= PRICE_MAX ? '+' : '' }} €</div>
          <input
            v-model.number="priceMax"
            class="range"
            type="range"
            :min="2000"
            :max="PRICE_MAX"
            :step="1000"
            @change="resetPageAndPush"
          >
        </div>

        <div class="fgroup">
          <h4>Läbisõit kuni</h4>
          <div class="slval mono">{{ fmtNum(kmMax) }}{{ kmMax >= KM_MAX ? '+' : '' }} km</div>
          <input
            v-model.number="kmMax"
            class="range"
            type="range"
            :min="20000"
            :max="KM_MAX"
            :step="10000"
            @change="resetPageAndPush"
          >
        </div>

        <div class="fgroup">
          <h4>Kütus</h4>
          <button
            v-for="f in fuelOptions"
            :key="f.value"
            type="button"
            class="fopt"
            :class="{ on: fuel === f.value }"
            @click="toggleFuel(f.value)"
          >
            <span class="box"><Icon :name="fuel === f.value ? 'check' : 'plus'" :size="12" /></span>
            <span class="flabel">{{ f.label }}</span>
          </button>
        </div>

        <div class="fgroup">
          <h4>Käigukast</h4>
          <button
            v-for="t in transmissionOptions"
            :key="t.value"
            type="button"
            class="fopt"
            :class="{ on: transmission === t.value }"
            @click="toggleTransmission(t.value)"
          >
            <span class="box"><Icon :name="transmission === t.value ? 'check' : 'plus'" :size="12" /></span>
            <span class="flabel">{{ t.label }}</span>
          </button>
        </div>
      </aside>

      <!-- results column -->
      <main class="res-main" aria-live="polite">
        <div class="res-head">
          <div class="res-count">
            <template v-if="!pending"><b class="mono">{{ fmtNum(total) }}</b> autot leitud</template>
            <template v-else>Otsin…</template>
          </div>
          <div class="sortwrap">
            <button type="button" class="sortbtn" @click="sortOpen = !sortOpen">
              <Icon name="arrow-down-up" :size="15" />{{ sortLabel }}<Icon name="chevron-down" :size="15" />
            </button>
            <div v-if="sortOpen" class="sortmenu" @mouseleave="sortOpen = false">
              <button
                v-for="s in sortOptions"
                :key="s.id"
                type="button"
                :class="{ on: s.id === sort }"
                @click="pickSort(s.id)"
              >
                {{ s.label }}
              </button>
            </div>
          </div>
        </div>

        <!-- error -->
        <div v-if="error" class="empty">
          <Icon name="server-crash" :size="40" />
          <h3>Kuulutusi ei õnnestunud laadida</h3>
          <p>Server ei vasta. Käivita backend ja proovi uuesti.</p>
        </div>

        <!-- loading -->
        <div v-else-if="pending && !items.length" class="grid res-grid">
          <div v-for="n in 6" :key="n" class="ccard" aria-hidden="true" style="cursor: default;">
            <div class="photo skeleton" style="aspect-ratio: 3/2;" />
            <div class="cbody">
              <div class="skeleton" style="height: 18px; width: 70%;" />
              <div class="skeleton" style="height: 36px;" />
              <div class="skeleton" style="height: 14px; width: 50%;" />
            </div>
          </div>
        </div>

        <!-- results -->
        <div v-else-if="items.length" class="grid res-grid">
          <SignalCard v-for="listing in items" :key="listing.id" :listing="listing" />
        </div>

        <!-- empty -->
        <div v-else class="empty">
          <Icon name="search-x" :size="40" />
          <h3>Ühtegi autot ei leitud</h3>
          <p>Proovi filtreid lõdvendada või muuda otsingusõna.</p>
          <button type="button" class="btn-volt" @click="clearAll">Tühjenda filtrid</button>
        </div>

        <!-- pagination -->
        <nav v-if="totalPages > 1" class="pagination" aria-label="Lehekülgede navigeerimine">
          <button type="button" class="btn-ghost" :disabled="page <= 1" @click="goToPage(page - 1)">
            <Icon name="arrow-left" :size="15" />Eelmine
          </button>
          <span class="mono">{{ page }} / {{ totalPages }}</span>
          <button type="button" class="btn-ghost" :disabled="page >= totalPages" @click="goToPage(page + 1)">
            Järgmine<Icon name="arrow-right" :size="15" />
          </button>
        </nav>
      </main>
    </div>

    <DarkFooter />
  </div>
</template>

<style scoped>
.res-main { min-height: 50vh; }
.pagination {
  display: flex; align-items: center; justify-content: center; gap: 18px;
  margin: 36px 0 8px; color: var(--muted-l);
}
.pagination .btn-ghost { padding: 9px 16px; font-size: 14px; }
.pagination .btn-ghost:disabled { opacity: .4; cursor: default; }
</style>
