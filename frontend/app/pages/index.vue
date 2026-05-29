<script setup lang="ts">
import { useListings } from '~/composables/useListings'
import type { ListingsQuery } from '~/types/listing'

useSeoMeta({
  title: 'auto48 — kirjelda autot, leiame selle',
  description: 'Eesti uue põlvkonna autoturg. Nutiotsing tehisaruga, taustakontroll igal autol ja hinnabaromeeter — leia auto, mida usaldad.',
})

const router = useRouter()

// Recommended cars (real listings, newest first).
const recQuery = ref<ListingsQuery>({ limit: 8, sort: 'newest' })
const { data, pending } = useListings(recQuery)
const recommended = computed(() => data.value?.items ?? [])
const totalCount = computed(() => data.value?.total ?? 0)
const totalLabel = computed(() => totalCount.value.toLocaleString('et-EE'))

// AI command bar.
const aiText = ref('')
function search(q?: string) {
  const term = (q ?? aiText.value).trim()
  router.push({ path: '/search', query: term ? { q: term } : {} })
}

const aiPrompts = [
  'töökindel pereauto kuni 8000 €',
  'säästlik linnaauto väikese läbisõiduga',
  'nelikvedu talveks, automaatkast',
  'elektriauto, mille aku on hea',
]

const features = [
  { icon: 'sparkles', h: 'Nutiotsing', p: 'Otsi tavakeeles — tehisaru tõlgib su soovi filtriteks ja järjestab autod sobivuse järgi.' },
  { icon: 'shield-check', h: 'Taustakontroll', p: 'Iga auto läbisõit, õnnetuste ajalugu, arestid ja ülevaatus on automaatselt kontrollitud.' },
  { icon: 'badge-euro', h: 'Hinnabaromeeter', p: 'Näeme tuhandeid tehinguid — iga kuulutuse juures näitame, kas hind on turuga võrreldes aus.' },
]
</script>

<template>
  <div>
    <!-- dark hero region -->
    <div class="dark">
      <div class="dots" />

      <nav class="nav">
        <NuxtLink to="/" class="wordmark">auto48<span class="dot" /></NuxtLink>
        <div class="navlinks">
          <NuxtLink to="/search">Osta</NuxtLink>
          <NuxtLink to="/sell">Müü</NuxtLink>
          <a href="#">Finantseerimine</a>
          <NuxtLink to="/search">Hinnabaromeeter</NuxtLink>
        </div>
        <div class="navright">
          <button type="button" class="lng"><Icon name="globe" :size="15" />ET</button>
          <NuxtLink to="/sell" class="login">Logi sisse</NuxtLink>
          <NuxtLink to="/sell" class="btn-volt"><Icon name="plus" :size="15" />Lisa kuulutus</NuxtLink>
        </div>
      </nav>

      <header class="hero">
        <div class="kicker"><Icon name="sparkles" :size="13" />Nutiotsing tehisaruga</div>
        <h1>Kirjelda autot.<br><span class="gl">Leiame selle.</span></h1>
        <p class="sub">
          Ei mingit filtrite labürinti. Ütle, mida vajad — auto48 leiab sobivad autod,
          kontrollib tausta ja näitab, kas hind on aus.
        </p>

        <form class="cmd" @submit.prevent="search()">
          <Icon name="sparkles" :size="22" class="spark" />
          <input
            v-model="aiText"
            type="search"
            placeholder="nt töökindel pereauto kuni 8000 €, väike läbisõit"
            aria-label="Nutiotsing"
          >
          <button type="submit" class="go"><Icon name="arrow-up" :size="17" />Otsi</button>
        </form>

        <div class="chips">
          <button v-for="p in aiPrompts" :key="p" type="button" class="chip" @click="search(p)">{{ p }}</button>
        </div>

        <div class="hstats">
          <div class="hstat"><div class="n">{{ totalLabel }}</div><div class="l">aktiivset autot</div></div>
          <div class="hstat"><div class="n">100%</div><div class="l">taustakontrolliga</div></div>
          <div class="hstat"><div class="n">18 päeva</div><div class="l">keskmine müügiaeg</div></div>
        </div>
      </header>

      <div class="catrail">
        <NuxtLink
          v-for="c in bodyCategories"
          :key="c.id"
          :to="{ path: '/search', query: { body: c.id } }"
          class="cpill"
        >
          <Icon :name="c.icon" :size="17" class="ci" />{{ c.label }}
        </NuxtLink>
      </div>
    </div>

    <!-- light body -->
    <div class="body">
      <div class="sec-head">
        <div class="ht">
          <h2>Soovituslikud autod</h2>
          <span class="ct mono">{{ recommended.length }} / {{ totalLabel }}</span>
        </div>
        <NuxtLink class="more" to="/search">Kõik autod<Icon name="arrow-right" :size="15" /></NuxtLink>
      </div>

      <div class="grid">
        <template v-if="pending && !recommended.length">
          <div v-for="n in 8" :key="n" class="ccard" aria-hidden="true" style="cursor: default;">
            <div class="photo skeleton" style="aspect-ratio: 3/2;" />
            <div class="cbody">
              <div class="skeleton" style="height: 18px; width: 70%;" />
              <div class="skeleton" style="height: 36px;" />
              <div class="skeleton" style="height: 14px; width: 50%;" />
            </div>
          </div>
        </template>
        <template v-else>
          <SignalCard v-for="listing in recommended" :key="listing.id" :listing="listing" />
        </template>
      </div>

      <div v-if="!pending && !recommended.length" class="state-msg">
        <h2>Veel ühtegi kuulutust pole</h2>
        <p>Ole esimene — <NuxtLink to="/sell" class="link">lisa oma auto</NuxtLink>.</p>
      </div>

      <div class="feat">
        <div v-for="f in features" :key="f.h" class="fcard">
          <div class="fi"><Icon :name="f.icon" :size="22" /></div>
          <h3>{{ f.h }}</h3>
          <p>{{ f.p }}</p>
        </div>
      </div>
    </div>

    <DarkFooter />
  </div>
</template>
