<template>
  <div class="auth-page">
    <img :src="heroScene" alt="JunoFish access scene" class="auth-image" />
    <div class="auth-film"></div>
    <div class="auth-grain"></div>

    <nav class="auth-nav">
      <button class="brand-button" type="button" @click="router.push('/')">
        <span class="brand-mark">JUNOFISH</span>
        <span class="brand-meta">Decision Preview</span>
      </button>

      <button class="back-home-btn" type="button" @click="router.push('/')">
        Back to home
      </button>
    </nav>

    <main class="auth-layout">
      <section class="auth-copy">
        <p class="auth-kicker">ACCESS / ACCOUNT</p>
        <h1>{{ authHeadline }}</h1>
        <p class="auth-intro">
          {{ authIntro }}
        </p>

        <div class="auth-flow">
          <div class="flow-row">
            <span>01</span>
            <p>{{ flowStepOne }}</p>
          </div>
          <div class="flow-row">
            <span>02</span>
            <p>{{ flowStepTwo }}</p>
          </div>
          <div class="flow-row">
            <span>03</span>
            <p>{{ flowStepThree }}</p>
          </div>
        </div>

        <p class="auth-footnote">
          The landing page stays public. Saved projects, reports, and the live workspace stay
          behind sign-in.
        </p>
      </section>

      <section class="auth-panel">
        <div class="panel-top">
          <div>
            <span class="panel-kicker">{{ isReturningToFlow ? 'Continue' : 'Welcome' }}</span>
            <h2>{{ panelHeadline }}</h2>
          </div>

          <div class="panel-header">
            <button
              class="mode-toggle"
              :class="{ active: mode === 'signin' }"
              @click="switchMode('signin')"
              type="button"
            >
              Sign in
            </button>
            <button
              class="mode-toggle"
              :class="{ active: mode === 'signup' }"
              @click="switchMode('signup')"
              type="button"
            >
              Sign up
            </button>
          </div>
        </div>

        <form class="auth-form" @submit.prevent="submit">
          <label v-if="mode === 'signup'" class="field">
            <span>Name</span>
            <input
              v-model.trim="form.name"
              type="text"
              placeholder="How your name should appear"
              :disabled="submitting"
            />
          </label>

          <label class="field">
            <span>Email</span>
            <input
              v-model.trim="form.email"
              type="email"
              placeholder="name@example.com"
              :disabled="submitting"
            />
          </label>

          <label class="field">
            <span>Password</span>
            <input
              v-model="form.password"
              type="password"
              placeholder="At least 8 characters"
              minlength="8"
              :disabled="submitting"
            />
          </label>

          <p v-if="errorMessage" class="status error">{{ errorMessage }}</p>
          <p v-if="successMessage" class="status success">{{ successMessage }}</p>

          <button class="submit-btn" type="submit" :disabled="submitting">
            <span v-if="submitting">Working...</span>
            <span v-else>{{ submitLabel }}</span>
          </button>
        </form>

        <div class="panel-note">
          <span>Next</span>
          <p>{{ nextStepCopy }}</p>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import heroScene from '../assets/hero/juno-fish-original.jpg'
import { authClient } from '../lib/auth-client'

const route = useRoute()
const router = useRouter()

const mode = ref('signin')
const submitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const form = reactive({
  name: '',
  email: '',
  password: ''
})

const redirectPath = computed(() => {
  return typeof route.query.redirect === 'string' ? route.query.redirect : '/'
})

const destinationLabel = computed(() => {
  const redirect = redirectPath.value

  if (redirect.startsWith('/process/')) return 'your project setup'
  if (redirect.startsWith('/simulation/')) return 'your simulation workspace'
  if (redirect.startsWith('/report/')) return 'your report'
  if (redirect.startsWith('/interaction/')) return 'your report chat'
  return 'JunoFish'
})

const isReturningToFlow = computed(() => redirectPath.value !== '/')

const authHeadline = computed(() => {
  if (isReturningToFlow.value) {
    return `Continue to ${destinationLabel.value}.`
  }

  return mode.value === 'signin'
    ? 'Sign in to start or reopen a project.'
    : 'Create your JunoFish account.'
})

const authIntro = computed(() => {
  if (isReturningToFlow.value) {
    return 'Your place is being held. Sign in or create an account and you will go straight back to where you were heading.'
  }

  return 'Use email and password to save projects, reopen earlier work, and move from the public landing page into the full app.'
})

const flowStepOne = computed(() => {
  return isReturningToFlow.value
    ? 'Sign in with your email, or create an account if this is your first visit.'
    : 'Create an account in a few seconds with email and password.'
})

const flowStepTwo = computed(() => {
  return isReturningToFlow.value
    ? `We will send you straight back to ${destinationLabel.value}.`
    : 'Your work and saved projects stay attached to your account.'
})

const flowStepThree = computed(() => {
  return isReturningToFlow.value
    ? 'From there, you can continue the setup without starting over.'
    : 'You can always browse first and sign in only when you need the full workspace.'
})

const panelHeadline = computed(() => {
  return mode.value === 'signin' ? 'Enter JunoFish' : 'Create account'
})

const submitLabel = computed(() => {
  if (mode.value === 'signin') {
    return isReturningToFlow.value ? 'Sign in and continue' : 'Sign in'
  }

  return isReturningToFlow.value ? 'Create account and continue' : 'Create account'
})

const nextStepCopy = computed(() => {
  return isReturningToFlow.value
    ? `After sign-in, we will return you to ${destinationLabel.value}.`
    : 'After sign-in, you can launch a new project or reopen a previous one.'
})

const getRedirectTarget = () => {
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
  return redirect || '/'
}

const resetStatus = () => {
  errorMessage.value = ''
  successMessage.value = ''
}

const switchMode = (nextMode) => {
  mode.value = nextMode
  resetStatus()
}

const submit = async () => {
  resetStatus()

  if (mode.value === 'signup' && !form.name) {
    errorMessage.value = 'Please enter a display name.'
    return
  }

  if (!form.email || !form.password) {
    errorMessage.value = 'Please enter both email and password.'
    return
  }

  submitting.value = true

  try {
    if (mode.value === 'signup') {
      const signUpResult = await authClient.signUp.email({
        name: form.name,
        email: form.email,
        password: form.password
      })

      if (signUpResult.error) {
        errorMessage.value = signUpResult.error.message || 'Sign-up failed.'
        return
      }

      successMessage.value = 'Account created. Signing you in...'
    }

    const signInResult = await authClient.signIn.email({
      email: form.email,
      password: form.password
    })

    if (signInResult.error) {
      errorMessage.value = signInResult.error.message || 'Sign-in failed.'
      return
    }

    await router.replace(getRedirectTarget())
  } catch (error) {
    errorMessage.value = error?.message || 'Authentication request failed.'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.auth-page {
  --ink: #071017;
  --paper: rgba(246, 239, 229, 0.94);
  --paper-line: rgba(7, 16, 23, 0.12);
  --orange: #ff7a3d;
  min-height: 100svh;
  position: relative;
  overflow: hidden;
  color: #ffffff;
  background: #0b1116;
}

.auth-image,
.auth-film,
.auth-grain {
  position: absolute;
  inset: 0;
}

.auth-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center center;
  transform: scale(1.04);
}

.auth-film {
  background:
    linear-gradient(92deg, rgba(6, 12, 16, 0.92) 0%, rgba(6, 12, 16, 0.76) 42%, rgba(6, 12, 16, 0.34) 100%),
    linear-gradient(180deg, rgba(6, 12, 16, 0.2) 0%, rgba(6, 12, 16, 0.12) 100%);
}

.auth-grain {
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
  background-size: 120px 120px;
  opacity: 0.22;
}

.auth-nav,
.auth-layout {
  position: relative;
  z-index: 2;
  width: min(1480px, calc(100% - 48px));
  margin: 0 auto;
}

.auth-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 26px;
}

.brand-button,
.back-home-btn,
.auth-kicker,
.brand-mark,
.brand-meta,
.flow-row span,
.panel-kicker,
.mode-toggle,
.field span,
.submit-btn,
.panel-note span {
  font-family: 'JetBrains Mono', monospace;
}

.brand-button {
  display: grid;
  gap: 4px;
  border: 0;
  background: transparent;
  color: #ffffff;
  text-align: left;
  cursor: pointer;
}

.brand-mark {
  font-size: 1rem;
  font-weight: 800;
  letter-spacing: 0.24em;
}

.brand-meta {
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.62);
}

.back-home-btn {
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.06);
  color: #ffffff;
  padding: 12px 16px;
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  cursor: pointer;
  backdrop-filter: blur(14px);
  transition: transform 0.22s ease, background 0.22s ease;
}

.back-home-btn:hover,
.submit-btn:hover {
  transform: translateY(-2px);
}

.auth-layout {
  min-height: calc(100svh - 96px);
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(320px, 0.66fr);
  gap: 52px;
  align-items: end;
  padding-bottom: 46px;
}

.auth-copy {
  max-width: 660px;
  padding-top: 72px;
}

.auth-copy > * {
  opacity: 0;
  transform: translateY(20px);
  animation: authReveal 0.75s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.auth-copy > *:nth-child(1) {
  animation-delay: 0.06s;
}

.auth-copy > *:nth-child(2) {
  animation-delay: 0.14s;
}

.auth-copy > *:nth-child(3) {
  animation-delay: 0.22s;
}

.auth-copy > *:nth-child(4) {
  animation-delay: 0.3s;
}

.auth-copy > *:nth-child(5) {
  animation-delay: 0.38s;
}

.auth-kicker {
  margin-bottom: 18px;
  font-size: 0.78rem;
  letter-spacing: 0.14em;
  color: rgba(255, 255, 255, 0.78);
}

.auth-copy h1 {
  max-width: 620px;
  font-size: clamp(2.6rem, 6vw, 5.4rem);
  line-height: 0.94;
  letter-spacing: -0.06em;
}

.auth-intro {
  max-width: 560px;
  margin-top: 22px;
  font-size: 1.02rem;
  line-height: 1.72;
  color: rgba(255, 255, 255, 0.8);
}

.auth-flow {
  display: grid;
  gap: 16px;
  margin-top: 34px;
}

.flow-row {
  display: grid;
  grid-template-columns: 40px 1fr;
  gap: 14px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.18);
}

.flow-row span {
  color: rgba(255, 255, 255, 0.62);
  font-size: 0.8rem;
}

.flow-row p {
  color: rgba(255, 255, 255, 0.76);
  line-height: 1.62;
}

.auth-footnote {
  max-width: 520px;
  margin-top: 26px;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.6;
}

.auth-panel {
  align-self: center;
  padding: 28px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background:
    linear-gradient(180deg, rgba(247, 240, 230, 0.94), rgba(255, 251, 245, 0.92)),
    radial-gradient(circle at top right, rgba(255, 122, 61, 0.08), transparent 30%);
  color: var(--ink);
  box-shadow: 0 28px 80px rgba(0, 0, 0, 0.18);
  backdrop-filter: blur(14px);
}

.panel-top {
  display: grid;
  gap: 18px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--paper-line);
}

.panel-kicker {
  display: inline-flex;
  margin-bottom: 8px;
  font-size: 0.74rem;
  letter-spacing: 0.14em;
  color: var(--orange);
}

.panel-top h2 {
  font-size: clamp(1.8rem, 3vw, 2.7rem);
  line-height: 0.98;
  letter-spacing: -0.05em;
}

.panel-header {
  display: inline-grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 6px;
  background: rgba(7, 16, 23, 0.05);
}

.mode-toggle {
  border: 0;
  padding: 14px 16px;
  background: transparent;
  color: rgba(7, 16, 23, 0.72);
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: background 0.22s ease, color 0.22s ease;
}

.mode-toggle.active {
  background: #111111;
  color: #ffffff;
}

.auth-form {
  display: grid;
  gap: 18px;
  padding-top: 24px;
}

.field {
  display: grid;
  gap: 8px;
}

.field span {
  font-size: 0.76rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(7, 16, 23, 0.62);
}

.field input {
  width: 100%;
  padding: 16px 18px;
  border: 1px solid rgba(7, 16, 23, 0.12);
  background: rgba(255, 255, 255, 0.78);
  font: inherit;
  color: var(--ink);
  outline: none;
  transition: border-color 0.22s ease, background 0.22s ease;
}

.field input:focus {
  border-color: rgba(255, 122, 61, 0.56);
  background: rgba(255, 255, 255, 0.96);
}

.status {
  font-size: 0.92rem;
  line-height: 1.55;
}

.status.error {
  color: #b42318;
}

.status.success {
  color: #0f766e;
}

.submit-btn {
  border: 0;
  padding: 16px 20px;
  background: linear-gradient(135deg, #071017 0%, #183446 100%);
  color: #ffffff;
  font-size: 0.82rem;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: transform 0.22s ease, opacity 0.22s ease;
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: wait;
}

.panel-note {
  display: grid;
  gap: 8px;
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid var(--paper-line);
}

.panel-note span {
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  color: rgba(7, 16, 23, 0.48);
}

.panel-note p {
  color: rgba(7, 16, 23, 0.74);
  line-height: 1.58;
}

@keyframes authReveal {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1080px) {
  .auth-layout {
    grid-template-columns: 1fr;
    align-items: start;
    gap: 34px;
    padding-top: 40px;
  }

  .auth-panel {
    max-width: 620px;
  }
}

@media (max-width: 780px) {
  .auth-nav,
  .auth-layout {
    width: min(100%, calc(100% - 32px));
  }

  .auth-nav {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .auth-layout {
    min-height: auto;
    padding-bottom: 28px;
  }

  .auth-copy {
    padding-top: 12px;
  }

  .back-home-btn {
    width: 100%;
  }
}

@media (max-width: 560px) {
  .auth-panel {
    padding: 22px 18px;
  }

  .flow-row {
    grid-template-columns: 32px 1fr;
  }
}
</style>
