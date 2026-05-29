<script setup lang="ts">
/** Sticky light top nav used on the search and detail pages. */
const props = withDefaults(defineProps<{ query?: string }>(), { query: '' })

const router = useRouter()
const q = ref(props.query)
watch(() => props.query, v => (q.value = v))

function submit() {
  router.push({ path: '/search', query: q.value.trim() ? { q: q.value.trim() } : {} })
}
</script>

<template>
  <nav class="lnav">
    <NuxtLink to="/" class="wordmark">auto48<span class="dot" /></NuxtLink>

    <form class="lsearch" @submit.prevent="submit">
      <Icon name="sparkles" :size="17" class="spark" />
      <input
        v-model="q"
        type="search"
        placeholder="Kirjelda autot või otsi marki…"
        aria-label="Otsing"
      >
      <button type="submit" class="lgo" aria-label="Otsi">
        <Icon name="arrow-right" :size="16" />
      </button>
    </form>

    <div class="lnav-right">
      <button type="button" class="lng"><Icon name="globe" :size="15" />ET</button>
      <NuxtLink to="/search" class="ghost"><Icon name="heart" :size="16" /><span>Salvestatud</span></NuxtLink>
      <NuxtLink to="/sell" class="btn-volt"><Icon name="plus" :size="15" />Lisa kuulutus</NuxtLink>
    </div>
  </nav>
</template>
