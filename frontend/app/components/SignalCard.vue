<script setup lang="ts">
import type { Listing } from '~/types/listing'
import { formatEur, formatMileage } from '~/types/listing'
import type { ValuationParams } from '~/composables/useValuation'

/**
 * Listing card in the Signal style. Renders only real listing data.
 * The fairness chip is fetched from /v1/valuations lazily on the client
 * (after mount) so server-side rendering of grids stays fast.
 */
const props = withDefaults(
  defineProps<{ listing: Listing, valuate?: boolean }>(),
  { valuate: true },
)

const saved = ref(false)

// Client-only valuation: params stay null during SSR, set after mount.
const valParams = ref<ValuationParams | null>(null)
onMounted(() => {
  if (!props.valuate) return
  valParams.value = {
    make: props.listing.vehicle.make,
    model: props.listing.vehicle.model,
    year: props.listing.vehicle.year,
    mileage_km: props.listing.mileage_km ?? undefined,
    price_eur_cents: props.listing.price_eur_cents,
  }
})
const { fairness } = useValuation(valParams)
const showFair = computed(() => props.valuate && fairness.value.key !== 'unknown')
</script>

<template>
  <NuxtLink
    :to="`/listings/${listing.id}`"
    class="ccard"
    :aria-label="`${listing.vehicle.make} ${listing.vehicle.model}, ${formatEur(listing.price_eur_cents)}`"
  >
    <div style="position: relative;">
      <CarPhoto :url="listing.thumbnail_url" :seed="listing.id" :alt="`${listing.vehicle.make} ${listing.vehicle.model}`" />
      <span v-if="listing.status === 'sold'" class="vbadge">Müüdud</span>
      <button
        type="button"
        class="save"
        :class="{ on: saved }"
        :aria-pressed="saved"
        aria-label="Salvesta"
        @click.prevent="saved = !saved"
      >
        <Icon name="heart" :size="15" />
      </button>
    </div>

    <div class="cbody">
      <div class="crow1">
        <div>
          <div class="ctitle">{{ listing.vehicle.make }} {{ listing.vehicle.model }}</div>
          <div v-if="listing.vehicle.variant" class="cvar">{{ listing.vehicle.variant }}</div>
        </div>
        <div class="cprice">{{ formatEur(listing.price_eur_cents) }}</div>
      </div>

      <div class="specs">
        <span class="s"><Icon name="calendar" :size="13" />{{ listing.vehicle.year }}</span>
        <span class="s"><Icon name="gauge" :size="13" />{{ formatMileage(listing.mileage_km) }}</span>
        <span class="s"><Icon :name="fuelIcon[listing.vehicle.fuel]" :size="13" />{{ fuelLabel[listing.vehicle.fuel] }}</span>
        <span class="s"><Icon name="cog" :size="13" />{{ transmissionLabel[listing.vehicle.transmission] }}</span>
      </div>

      <div class="cfoot">
        <span v-if="showFair" class="fair" :class="fairness.key">
          <Icon :name="fairness.icon" :size="12" />{{ fairness.short }}
        </span>
        <span v-else />
        <span v-if="listing.location_county" class="loc">
          <Icon name="map-pin" :size="12" />{{ listing.location_county }}
        </span>
      </div>
    </div>
  </NuxtLink>
</template>
