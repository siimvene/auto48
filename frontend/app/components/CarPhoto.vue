<script setup lang="ts">
/**
 * Vehicle photo with a deterministic dark-gradient fallback (matching the
 * Signal design) when no real photo URL is available.
 */
const props = withDefaults(
  defineProps<{ url?: string | null, seed?: number, alt?: string, big?: boolean }>(),
  { url: null, seed: 1, alt: '', big: false },
)

const gradient = computed(() => placeholderGradient(props.seed))
</script>

<template>
  <div class="photo" :style="url ? undefined : { background: gradient }">
    <img v-if="url" :src="url" :alt="alt" loading="lazy">
    <div v-else class="ph-ic" aria-hidden="true">
      <Icon name="car-front" :size="big ? 132 : 84" />
    </div>
  </div>
</template>
