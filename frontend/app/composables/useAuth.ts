/**
 * useAuth — SSR-friendly auth state for auto48.
 * JWT is persisted in a cookie (`auto48_token`); user profile is stored in
 * a shared `useState` ref so it survives navigations within the same session.
 */

interface User {
  id: number
  email: string
  display_name: string
}

interface RegisterPayload {
  email: string
  password: string
  display_name: string
  seller_type: 'PRIVATE' | 'DEALER'
}

interface RegisterResponse {
  user: User
  access_token: string
}

interface LoginResponse {
  access_token: string
  token_type: string
}

export function useAuth() {
  const config = useRuntimeConfig()

  // Token stored in a cookie so it survives page reloads (SSR-safe).
  const token = useCookie<string | null>('auto48_token', {
    maxAge: 60 * 60 * 24 * 7, // 7 days
    sameSite: 'lax',
    path: '/',
  })

  // User profile shared across the app via useState.
  const user = useState<User | null>('auth_user', () => null)

  const isLoggedIn = computed(() => !!token.value)

  /** Returns Authorization header object, or empty object when not logged in. */
  function authHeaders(): Record<string, string> {
    if (!token.value) return {}
    return { Authorization: `Bearer ${token.value}` }
  }

  /** Fetch current user from /v1/auth/me and populate user state. */
  async function fetchMe(): Promise<void> {
    if (!token.value) return
    try {
      const me = await $fetch<User>('/v1/auth/me', {
        baseURL: config.public.apiBase,
        headers: authHeaders(),
      })
      user.value = me
    } catch (err: unknown) {
      // Invalid / expired token — clear auth state
      token.value = null
      user.value = null
    }
  }

  /** Register a new account; stores token and fetches user profile on success. */
  async function register(payload: RegisterPayload): Promise<void> {
    try {
      const res = await $fetch<RegisterResponse>('/v1/auth/register', {
        baseURL: config.public.apiBase,
        method: 'POST',
        body: payload,
      })
      token.value = res.access_token
      await fetchMe()
    } catch (err: unknown) {
      const e = err as { statusCode?: number; data?: { detail?: string; message?: string }; statusMessage?: string }
      const status = e?.statusCode
      if (status === 409) {
        throw new Error('See e-posti aadress on juba kasutusel.')
      } else if (status === 422) {
        throw new Error('Kontrolli sisestatud andmeid.')
      }
      const msg = e?.data?.detail ?? e?.data?.message ?? e?.statusMessage ?? 'Registreerimine ebaõnnestus. Proovi hiljem uuesti.'
      throw new Error(msg)
    }
  }

  /** Login with email + password; stores token and fetches user profile on success. */
  async function login(email: string, password: string): Promise<void> {
    try {
      const res = await $fetch<LoginResponse>('/v1/auth/login', {
        baseURL: config.public.apiBase,
        method: 'POST',
        body: { email, password },
      })
      token.value = res.access_token
      await fetchMe()
    } catch (err: unknown) {
      const e = err as { statusCode?: number; data?: { detail?: string; message?: string }; statusMessage?: string }
      const status = e?.statusCode
      if (status === 401 || status === 403) {
        throw new Error('Vale e-posti aadress või parool.')
      }
      const msg = e?.data?.detail ?? e?.data?.message ?? e?.statusMessage ?? 'Sisselogimine ebaõnnestus. Proovi hiljem uuesti.'
      throw new Error(msg)
    }
  }

  /** Clear auth state and redirect to home. */
  function logout(): void {
    token.value = null
    user.value = null
    navigateTo('/')
  }

  return {
    token,
    user,
    isLoggedIn,
    authHeaders,
    fetchMe,
    register,
    login,
    logout,
  }
}
