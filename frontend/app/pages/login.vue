<script setup lang="ts">
useSeoMeta({
  title: 'Logi sisse — auto48',
  description: 'Logi sisse oma auto48 kontole.',
})

const { login, isLoggedIn } = useAuth()
const route = useRoute()
const router = useRouter()

// If already logged in, redirect away immediately
if (isLoggedIn.value) {
  const target = (route.query.redirect as string) || '/sell'
  await navigateTo(target, { replace: true })
}

const email = ref('')
const password = ref('')
const pending = ref(false)
const errorMsg = ref<string | null>(null)

async function submit() {
  errorMsg.value = null
  if (!email.value.trim() || !password.value) {
    errorMsg.value = 'Palun sisesta e-posti aadress ja parool.'
    return
  }

  pending.value = true
  try {
    await login(email.value.trim(), password.value)
    const target = (route.query.redirect as string) || '/sell'
    await router.push(target)
  } catch (err: unknown) {
    errorMsg.value = (err as Error).message
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div>
    <LightNav />
    <div class="auth-page__inner">
      <div class="auth-card">
        <header class="auth-card__header">
          <h1 class="auth-card__title">Logi sisse</h1>
          <p class="auth-card__sub">Tere tulemast tagasi auto48-le.</p>
        </header>

        <form novalidate @submit.prevent="submit">
          <div class="field">
            <label class="field__label" for="email">E-posti aadress <span class="required" aria-hidden="true">*</span></label>
            <input
              id="email"
              v-model="email"
              class="field__input"
              type="email"
              placeholder="sina@näide.ee"
              autocomplete="email"
              required
            />
          </div>

          <div class="field" style="margin-top: 14px;">
            <label class="field__label" for="password">Parool <span class="required" aria-hidden="true">*</span></label>
            <input
              id="password"
              v-model="password"
              class="field__input"
              type="password"
              placeholder="••••••••"
              autocomplete="current-password"
              required
            />
          </div>

          <p v-if="errorMsg" class="auth-error" role="alert">{{ errorMsg }}</p>

          <button
            type="submit"
            class="btn btn--primary btn--lg block"
            style="margin-top: 22px;"
            :disabled="pending"
          >
            <span v-if="pending" class="spinner" aria-hidden="true" />
            {{ pending ? 'Loginud sisse…' : 'Logi sisse' }}
          </button>
        </form>

        <p class="auth-card__switch">
          Pole veel kontot?
          <NuxtLink :to="`/register${route.query.redirect ? '?redirect=' + route.query.redirect : ''}`">Registreeru</NuxtLink>
        </p>
      </div>
    </div>
    <DarkFooter />
  </div>
</template>

<style scoped>
.auth-page__inner {
  max-width: 440px;
  margin: 0 auto;
  padding: 48px 20px 80px;
}

.auth-card {
  background: var(--surface);
  border: 1px solid var(--line-l);
  border-radius: 18px;
  padding: 36px 32px;
}

.auth-card__header { margin-bottom: 24px; }
.auth-card__title {
  font-family: var(--space);
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -.025em;
  color: var(--ink);
  margin: 0 0 6px;
}
.auth-card__sub { font-size: 15px; color: var(--muted-l); margin: 0; }

.field { display: flex; flex-direction: column; gap: 6px; }
.field__label { font-size: 13.5px; font-weight: 600; color: var(--ink); }
.required { color: var(--neg); }
.field__input {
  padding: 11px 14px;
  border: 1px solid var(--line-l);
  border-radius: 10px;
  font: inherit;
  font-size: 15px;
  color: var(--ink);
  background: var(--page);
  transition: border-color .2s, box-shadow .2s, background .2s;
  width: 100%;
  box-sizing: border-box;
}
.field__input:focus {
  outline: none;
  border-color: var(--volt-2);
  box-shadow: 0 0 0 3px rgba(174, 224, 43, .16);
  background: var(--surface);
}

.auth-error {
  font-size: 13.5px;
  color: var(--neg);
  margin: 14px 0 0;
  padding: 10px 14px;
  background: rgba(192, 73, 43, .07);
  border: 1px solid rgba(192, 73, 43, .3);
  border-radius: 10px;
}

.auth-card__switch {
  margin-top: 20px;
  text-align: center;
  font-size: 14px;
  color: var(--muted-l);
}
.auth-card__switch a {
  color: var(--ink);
  font-weight: 600;
  text-decoration: none;
}
.auth-card__switch a:hover { text-decoration: underline; }

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-weight: 700;
  border-radius: 11px;
  cursor: pointer;
  border: none;
  text-decoration: none;
  font-family: inherit;
  transition: background .2s, transform .15s, opacity .2s;
}
.btn:disabled { opacity: .55; cursor: not-allowed; }
.btn--primary { background: var(--volt); color: var(--volt-ink); padding: 12px 22px; font-size: 15px; }
.btn--primary:hover:not(:disabled) { background: var(--volt-2); transform: translateY(-1px); }
.btn--lg { padding: 15px 40px; font-size: 16px; }
.block { width: 100%; }

@keyframes spin { to { transform: rotate(360deg); } }
.spinner {
  display: inline-block;
  width: 1em;
  height: 1em;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin .7s linear infinite;
  flex-shrink: 0;
}
</style>
