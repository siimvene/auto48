<script setup lang="ts">
import { Icon as IconifyIcon } from '@iconify/vue'

/**
 * Thin wrapper around @iconify/vue using the bundled Lucide set.
 * Usage: <Icon name="car-front" :size="18" /> → renders lucide:car-front.
 */
const props = withDefaults(
  defineProps<{ name: string, size?: number | string }>(),
  { size: 16 },
)
</script>

<template>
  <IconifyIcon
    :icon="`lucide:${props.name}`"
    :width="props.size"
    :height="props.size"
    class="iconify"
  />
</template>

<style scoped>
.iconify {
  display: inline-block;
  vertical-align: middle;
  flex-shrink: 0;
}
</style>
