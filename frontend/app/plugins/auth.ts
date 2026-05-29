/**
 * auth.ts — Universal plugin that rehydrates the user profile from an
 * existing token cookie on every page load (SSR + client).
 *
 * Without this, `user` state would be null after a hard reload even when
 * the token cookie is still valid, so the nav would flash "Logi sisse".
 */
export default defineNuxtPlugin(async () => {
  const { token, user, fetchMe } = useAuth()

  if (token.value && !user.value) {
    await fetchMe()
  }
})
