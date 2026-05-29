import { addCollection } from '@iconify/vue'
import lucide from '@iconify-json/lucide/icons.json'

/**
 * Register the bundled Lucide icon set so <Icon> renders synchronously,
 * server-side and offline — no runtime calls to the Iconify CDN.
 */
export default defineNuxtPlugin(() => {
  addCollection(lucide)
})
