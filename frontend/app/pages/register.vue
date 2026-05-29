<script setup lang="ts">
useSeoMeta({
  title: 'Registreeru — auto48',
  description: 'Loo auto48 konto, et lisada kuulutusi ja hallata oma müüke.',
})

const { register, isLoggedIn } = useAuth()
const route = useRoute()
const router = useRouter()

// If already logged in, redirect away immediately
if (isLoggedIn.value) {
  const target = (route.query.redirect as string) || '/sell'
  await navigateTo(target, { replace: true })
}

const email = ref('')
const password = ref('')
const displayName = ref('')
const sellerType = ref<'PRIVATE' | 'DEALER'>('PRIVATE')
const pending = ref(false)
const errorMsg = ref<string | null>(null)

interface FormErrors {
  email?: string
  password?: string
  displayName?: string
}
const errors = reactive<FormErrors>({})

function validateForm(): boolean {
  const e: FormErrors = {}
  if (!email.value.trim()) e.email = 'E-posti aadress on kohustuslik.'
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())) e.email = 'Sisesta kehtiv e-posti aadress.'
  if (!password.value || password.value.length < 8) e.password = 'Parool peab olema vähemalt 8 tähemärki.'
  if (!displayName.value.trim()) e.displayName = 'Nimi on kohustuslik.'
  Object.assign(errors, e)
  return Object.keys(e).length === 0
}

async function submit() {
  errorMsg.value = null
  // Clear previous field errors
  delete errors.email
  delete errors.password
  delete errors.displayName

  if (!validateForm()) return

  pending.value = true
  try {
    await register({
      email: email.value.trim(),
      password: password.value,
      display_name: displayName.value.trim(),
      seller_type: sellerType.value,
    })
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
          <h1 class="auth-card__title">Loo konto</h1>
          <p class="auth-card__sub">Registreeru — eraisikule tasuta.</p>
        </header>

        <form novalidate @submit.prevent="submit">
          <div class="field">
            <label class="field__label" for="display_name">Sinu nimi <span class="required" aria-hidden="true">*</span></label>
            <input
              id="display_name"
              v-model="displayName"
              class="field__input"
              :class="{ 'field__input--error': errors.displayName }"
              type="text"
              placeholder="Mati Maasikas"
              autocomplete="name"
              required
              @input="delete errors.displayName"
            />
            <p v-if="errors.displayName" class="field__error" role="alert">{{ errors.displayName }}</p>
          </div>

          <div class="field" style="margin-top: 14px;">
            <label class="field__label" for="reg_email">E-posti aadress <span class="required" aria-hidden="true">*</span></label>
            <input
              id="reg_email"
              v-model="email"
              class="field__input"
              :class="{ 'field__input--error': errors.email }"
              type="email"
              placeholder="sina@näide.ee"
              autocomplete="email"
              required
              @input="delete errors.email"
            />
            <p v-if="errors.email" class="field__error" role="alert">{{ errors.email }}</p>
          </div>

          <div class="field" style="margin-top: 14px;">
            <label class="field__label" for="reg_password">Parool <span class="required" aria-hidden="true">*</span></label>
            <input
              id="reg_password"
              v-model="password"
              class="field__input"
              :class="{ 'field__input--error': errors.password }"
              type="password"
              placeholder="Min. 8 tähemärki"
              autocomplete="new-password"
              required
              @input="delete errors.password"
            />
            <p v-if="errors.password" class="field__error" role="alert">{{ errors.password }}</p>
          </div>

          <div class="field" style="margin-top: 14px;">
            <label class="field__label">Müüja tüüp</label>
            <div class="seller-type-toggle">
              <button
                type="button"
                class="type-btn"
                :class="{ 'type-btn--active': sellerType === 'PRIVATE' }"
                @click="sellerType = 'PRIVATE'"
              >
                <Icon name="user" :size="16" />
                Eraisik
              </button>
              <button
                type="button"
                class="type-btn"
                :class="{ 'type-btn--active': sellerType === 'DEALER' }"
                @click="sellerType = 'DEALER'"
              >
                <Icon name="building-2" :size="16" />
                Esindustus
              </button>
            </div>
          </div>

          <p v-if="errorMsg" class="auth-error" role="alert">{{ errorMsg }}</p>

          <button
            type="submit"
            class="btn btn--primary btn--lg block"
            style="margin-top: 22px;"
            :disabled="pending"
          >
            <span v-if="pending" class="spinner" aria-hidden="true" />
            {{ pending ? 'Loon konto…' : 'Loo konto' }}
          </button>
        </form>

        <p class="auth-card__switch">
          Juba konto olemas?
          <NuxtLink :to="`/login${route.query.redirect ? '?redirect=' + route.query.redirect : ''}`">Logi sisse</NuxtLink>
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
.field__input--error { border-color: var(--neg); background: rgba(192, 73, 43, .06); }
.field__error { font-size: 12.5px; color: var(--neg); margin: 0; }

.seller-type-toggle {
  display: flex;
  gap: 10px;
}
.type-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid var(--line-l);
  background: var(--page);
  color: var(--muted-l);
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color .2s, background .2s, color .2s;
}
.type-btn--active {
  border-color: var(--volt-2);
  background: rgba(174, 224, 43, .1);
  color: var(--ink);
}
.type-btn:hover:not(.type-btn--active) { background: var(--surface); }

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
