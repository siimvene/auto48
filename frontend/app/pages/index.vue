<script setup lang="ts">
interface Listing {
  id: number
  make: string
  model: string
  year: number
  price_eur: number
  mileage_km: number | null
}
interface Page {
  items: Listing[]
  total: number
  limit: number
  offset: number
}

const config = useRuntimeConfig()
const { data, pending, error } = await useFetch<Page>('/v1/listings', {
  baseURL: config.public.apiBase,
  default: () => ({ items: [], total: 0, limit: 25, offset: 0 }),
})
</script>

<template>
  <main class="page">
    <h1>auto48</h1>
    <p class="tagline">Open car marketplace</p>

    <p v-if="pending">Loading listings…</p>
    <p v-else-if="error">Backend unavailable — start the API on {{ config.public.apiBase }}.</p>
    <p v-else-if="data && data.items.length === 0">No listings yet.</p>

    <ul v-else class="listings">
      <li v-for="listing in data?.items" :key="listing.id">
        <strong>{{ listing.make }} {{ listing.model }}</strong>
        <span>{{ listing.year }}</span>
        <span>{{ listing.price_eur.toLocaleString('et-EE') }} €</span>
      </li>
    </ul>
  </main>
</template>

<style scoped>
.page {
  max-width: 48rem;
  margin: 4rem auto;
  font-family: system-ui, sans-serif;
}
.tagline {
  color: #666;
}
.listings {
  list-style: none;
  padding: 0;
}
.listings li {
  display: flex;
  gap: 1rem;
  padding: 0.75rem 0;
  border-bottom: 1px solid #eee;
}
</style>
