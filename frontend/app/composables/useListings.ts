import type { Listing, ListingsQuery, Page, Photo } from '~/types/listing'

/**
 * Fetch a paginated list of listings with optional facet filters.
 *
 * `query` should be a reactive ref/computed so useFetch re-runs on changes.
 * The key includes a JSON snapshot of the query so deduplication is per-params.
 */
export function useListings(query: Ref<ListingsQuery> | ComputedRef<ListingsQuery>) {
  const config = useRuntimeConfig()

  const params = computed(() => {
    const q = toValue(query)
    // Strip undefined/empty/null so the URL stays clean
    return Object.fromEntries(
      Object.entries(q).filter(([, v]) => v !== undefined && v !== null && v !== ''),
    ) as Record<string, string | number>
  })

  const key = computed(() => `listings:${JSON.stringify(params.value)}`)

  const {
    data,
    pending,
    error,
    refresh,
  } = useFetch<Page<Listing>>('/v1/listings', {
    baseURL: config.public.apiBase,
    query: params,
    key,
    default: (): Page<Listing> => ({ items: [], total: 0, limit: 25, offset: 0 }),
  })

  return {
    data,
    pending,
    error,
    refresh,
  }
}

/**
 * Fetch a single listing by id.
 *
 * `id` can be a ref, computed, or plain string/number — useFetch tracks it.
 */
export function useListing(id: Ref<string | number> | ComputedRef<string | number> | string | number) {
  const config = useRuntimeConfig()

  const key = computed(() => `listing:${toValue(id)}`)

  const {
    data,
    pending,
    error,
    refresh,
  } = useFetch<Listing | null>(() => `/v1/listings/${toValue(id)}`, {
    baseURL: config.public.apiBase,
    key,
    default: (): Listing | null => null,
  })

  return {
    data,
    pending,
    error,
    refresh,
  }
}

/**
 * Fetch photos for a listing by id.
 * Returns Photo[] from GET /v1/listings/{id}/photos.
 */
export function useListingPhotos(id: Ref<string | number> | ComputedRef<string | number> | string | number) {
  const config = useRuntimeConfig()

  const key = computed(() => `listing-photos:${toValue(id)}`)

  const {
    data,
    pending,
    error,
    refresh,
  } = useFetch<Photo[]>(() => `/v1/listings/${toValue(id)}/photos`, {
    baseURL: config.public.apiBase,
    key,
    default: (): Photo[] => [],
  })

  return {
    data,
    pending,
    error,
    refresh,
  }
}
