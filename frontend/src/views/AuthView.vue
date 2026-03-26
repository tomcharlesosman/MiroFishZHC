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
            <span class="panel-chip active">Email code</span>
            <span class="panel-chip">Ethereum wallet</span>
          </div>
        </div>

        <form class="auth-form" @submit.prevent="verifyEmailCode">
          <label class="field">
            <span>Email</span>
            <input
              v-model.trim="form.email"
              type="email"
              placeholder="name@example.com"
              :disabled="sendingCode || verifyingCode || connectingWallet"
            />
          </label>

          <div class="action-row">
            <button
              class="secondary-btn"
              type="button"
              :disabled="sendingCode || verifyingCode || connectingWallet"
              @click="requestEmailCode"
            >
              <span v-if="sendingCode">Sending...</span>
              <span v-else>{{ codeSent ? 'Resend code' : 'Send code' }}</span>
            </button>
            <span class="helper-text">First-time sign-in creates the account and provisions an embedded wallet.</span>
          </div>

          <label v-if="codeSent" class="field">
            <span>Verification code</span>
            <input
              v-model.trim="form.code"
              type="text"
              inputmode="numeric"
              placeholder="Enter the code from your inbox"
              :disabled="verifyingCode || connectingWallet"
            />
          </label>

          <p v-if="errorMessage" class="status error">{{ errorMessage }}</p>
          <p v-if="successMessage" class="status success">{{ successMessage }}</p>
          <p v-if="authState.error" class="status error">{{ authState.error }}</p>

          <button class="submit-btn" type="submit" :disabled="!codeSent || verifyingCode || connectingWallet">
            <span v-if="verifyingCode">Verifying...</span>
            <span v-else>{{ submitLabel }}</span>
          </button>
        </form>

        <div class="divider">
          <span>or</span>
        </div>

        <button
          class="wallet-btn"
          type="button"
          :disabled="sendingCode || verifyingCode || connectingWallet"
          @click="connectWallet"
        >
          <span v-if="connectingWallet">Connecting wallet...</span>
          <span v-else>{{ walletButtonLabel }}</span>
        </button>

        <div class="panel-note">
          <span>Next</span>
          <p>{{ nextStepCopy }}</p>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import heroScene from '../assets/hero/juno-fish-original.jpg'
import {
  getAuthState,
  initializeAuth,
  loginWithEmailCode,
  loginWithEthereumWallet,
  sendEmailCode
} from '../lib/auth-client'

const route = useRoute()
const router = useRouter()

const authState = getAuthState()
const codeSent = ref(false)
const sendingCode = ref(false)
const verifyingCode = ref(false)
const connectingWallet = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const form = reactive({
  email: '',
  code: ''
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

  return 'Sign in with email or wallet.'
})

const authIntro = computed(() => {
  if (isReturningToFlow.value) {
    return 'Your place is being held. Sign in with an email code or an Ethereum wallet and we will return you to the flow with a wallet-linked account.'
  }

  return 'Use a one-time email code for a fast sign-in, or connect an Ethereum wallet. Every account is provisioned with a wallet for web3-ready access.'
})

const flowStepOne = computed(() => {
  return isReturningToFlow.value
    ? 'Enter your email to receive a one-time code, or connect your Ethereum wallet.'
    : 'Use your email for a passwordless sign-in flow.'
})

const flowStepTwo = computed(() => {
  return isReturningToFlow.value
    ? `We will send you straight back to ${destinationLabel.value}.`
    : 'A first-time login creates the account and attaches an embedded wallet.'
})

const flowStepThree = computed(() => {
  return isReturningToFlow.value
    ? 'Wallet login stays available if you want to use an external wallet instead.'
    : 'Wallet login gives you a second path while preserving an embedded wallet on the account.'
})

const panelHeadline = computed(() => {
  return isReturningToFlow.value ? 'Confirm your access' : 'Enter JunoFish'
})

const submitLabel = computed(() => {
  return isReturningToFlow.value ? 'Verify and continue' : 'Verify email and enter JunoFish'
})

const walletButtonLabel = computed(() => {
  return isReturningToFlow.value ? 'Connect wallet and continue' : 'Use Ethereum wallet'
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

const requestEmailCode = async () => {
  resetStatus()

  if (!form.email) {
    errorMessage.value = 'Please enter an email address.'
    return
  }

  sendingCode.value = true

  try {
    await sendEmailCode(form.email)
    codeSent.value = true
    successMessage.value = 'Code sent. Check your inbox.'
  } catch (error) {
    errorMessage.value = error?.message || 'Failed to send the verification code.'
  } finally {
    sendingCode.value = false
  }
}

const verifyEmailCode = async () => {
  resetStatus()

  if (!form.email || !form.code) {
    errorMessage.value = 'Please enter both your email and the verification code.'
    return
  }

  verifyingCode.value = true

  try {
    await loginWithEmailCode(form.email, form.code)
    await router.replace(getRedirectTarget())
  } catch (error) {
    errorMessage.value = error?.message || 'Verification failed.'
  } finally {
    verifyingCode.value = false
  }
}

const connectWallet = async () => {
  resetStatus()
  connectingWallet.value = true

  try {
    await loginWithEthereumWallet()
    await router.replace(getRedirectTarget())
  } catch (error) {
    errorMessage.value = error?.message || 'Wallet login failed.'
  } finally {
    connectingWallet.value = false
  }
}

onMounted(async () => {
  try {
    await initializeAuth()
  } catch (error) {
    errorMessage.value = error?.message || 'Privy failed to initialize.'
  }
})
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
.panel-chip,
.field span,
.submit-btn,
.secondary-btn,
.wallet-btn,
.panel-note span,
.helper-text {
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
.submit-btn:hover,
.secondary-btn:hover,
.wallet-btn:hover {
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

.panel-chip {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  padding: 14px 16px;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  color: rgba(7, 16, 23, 0.72);
  background: rgba(255, 255, 255, 0.58);
}

.panel-chip.active {
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

.action-row {
  display: grid;
  gap: 10px;
}

.secondary-btn,
.wallet-btn {
  border: 1px solid rgba(7, 16, 23, 0.12);
  padding: 14px 18px;
  background: rgba(255, 255, 255, 0.88);
  color: var(--ink);
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: transform 0.22s ease, opacity 0.22s ease, background 0.22s ease;
}

.secondary-btn:disabled,
.wallet-btn:disabled,
.submit-btn:disabled {
  opacity: 0.7;
  cursor: wait;
}

.helper-text {
  font-size: 0.68rem;
  line-height: 1.6;
  color: rgba(7, 16, 23, 0.56);
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

.divider {
  display: grid;
  place-items: center;
  margin-top: 20px;
  margin-bottom: 16px;
}

.divider span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  padding: 4px 10px;
  border: 1px solid var(--paper-line);
  color: rgba(7, 16, 23, 0.56);
  font-size: 0.76rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
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
