<script setup lang="ts">
const route = useRoute()

const navLinks = [
  { label: 'Browse', to: '/' },
  { label: 'Sell your car', to: '/sell' },
] as const
</script>

<template>
  <header class="app-header">
    <div class="app-header__inner">
      <NuxtLink to="/" class="app-header__brand" aria-label="auto48 — home">
        <span class="app-header__logo">auto<strong>48</strong></span>
      </NuxtLink>

      <nav class="app-header__nav" aria-label="Main navigation">
        <NuxtLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          class="app-header__nav-link"
          :class="{ 'app-header__nav-link--active': route.path === link.to }"
        >
          {{ link.label }}
        </NuxtLink>
      </nav>

      <div class="app-header__actions">
        <NuxtLink to="/sell" class="btn btn--primary btn--sm">
          + List a car
        </NuxtLink>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgb(0 0 0 / 6%);
}

.app-header__inner {
  display: flex;
  align-items: center;
  gap: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.25rem;
  height: 60px;
}

.app-header__brand {
  text-decoration: none;
  flex-shrink: 0;
}

.app-header__logo {
  font-size: 1.35rem;
  font-family: system-ui, sans-serif;
  color: #111;
  letter-spacing: -0.02em;
}

.app-header__logo strong {
  color: #2563eb;
}

.app-header__nav {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex: 1;
}

.app-header__nav-link {
  padding: 0.375rem 0.75rem;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  color: #374151;
  text-decoration: none;
  transition: background 0.15s, color 0.15s;
}

.app-header__nav-link:hover {
  background: #f3f4f6;
  color: #111;
}

.app-header__nav-link--active {
  color: #2563eb;
  background: #eff6ff;
}

.app-header__actions {
  flex-shrink: 0;
}

/* shared button styles used across the app */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  border: none;
  text-decoration: none;
  transition: background 0.15s, transform 0.1s, box-shadow 0.15s;
  white-space: nowrap;
  font-family: inherit;
}

.btn--primary {
  background: #2563eb;
  color: #fff;
}

.btn--primary:hover {
  background: #1d4ed8;
  box-shadow: 0 2px 8px rgb(37 99 235 / 30%);
}

.btn--sm {
  padding: 0.4rem 0.9rem;
  font-size: 0.85rem;
}
</style>
