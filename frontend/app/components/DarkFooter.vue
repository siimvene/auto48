<script setup lang="ts">
/** Shared dark footer. */
const year = 2026
</script>

<template>
  <footer class="site">
    <div class="ftop">
      <NuxtLink to="/" class="wordmark" style="font-size: 22px;">auto48<span class="dot" /></NuxtLink>
      <div class="fcols">
        <div class="fcol">
          <h5>Ostjale</h5>
          <NuxtLink to="/search">Nutiotsing</NuxtLink>
          <NuxtLink to="/search">Hinnabaromeeter</NuxtLink>
          <a href="#">Finantseerimine</a>
          <NuxtLink to="/search">Salvestatud otsingud</NuxtLink>
        </div>
        <div class="fcol">
          <h5>Müüjale</h5>
          <NuxtLink to="/sell">Lisa kuulutus</NuxtLink>
          <a href="#">Esindustele</a>
          <a href="#">Hinnastamine</a>
        </div>
        <div class="fcol">
          <h5>auto48</h5>
          <a href="#">Meist</a>
          <a href="#">Kontakt</a>
          <a href="#">Abikeskus</a>
        </div>
      </div>
    </div>
    <p class="fnote mono">© {{ year }} auto48 — uue põlvkonna autoturg.</p>
  </footer>
</template>
