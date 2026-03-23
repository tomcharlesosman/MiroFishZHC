<template>
  <div class="home-container">
    <section class="hero-stage">
      <img :src="heroScene" alt="JunoFish strategy scene" class="hero-image" />
      <div class="hero-film"></div>
      <div class="hero-grain"></div>

      <nav class="navbar">
        <div class="nav-brand">
          <span class="nav-mark">JUNOFISH</span>
          <span class="nav-meta">Decision Preview</span>
        </div>

        <div class="nav-actions">
          <button class="nav-cta" @click="handleAccess">
            {{ accessLabel }}
          </button>
        </div>
      </nav>

      <div class="hero-layout">
        <div class="hero-copy">
          <p class="hero-kicker">FOR HIGH-STAKES COMPANY DECISIONS / v0.1 preview</p>
          <h1 class="hero-brand">JUNOFISH</h1>
          <p class="hero-headline">Explore how a company move might land before you make it.</p>
          <p class="hero-body">
            Start with the company website, add the few documents that matter, and get a clearer
            picture of how customers, partners, your team, and the market may respond.
          </p>

          <div class="hero-actions">
            <button class="hero-primary-btn" @click="scrollToSetup">Open Intake</button>
            <button class="hero-secondary-btn" @click="handleAccess">
              {{ session.data?.user ? 'Open Archive' : 'Sign In' }}
            </button>
          </div>

          <p class="hero-footnote">
            Take a look around first. Sign in when you want to save your work, start a project, or
            reopen an older one.
          </p>
        </div>

        <div class="hero-ledger" aria-label="JunoFish input sequence">
          <div class="ledger-line">
            <span class="ledger-index">01</span>
            <div>
              <strong>Start with the website</strong>
              <p>Use the homepage so JunoFish can understand what the company does and how it presents itself.</p>
            </div>
          </div>
          <div class="ledger-line">
            <span class="ledger-index">02</span>
            <div>
              <strong>Add the inside story</strong>
              <p>Upload decks, briefs, and notes that fill in what the public site does not say.</p>
            </div>
          </div>
          <div class="ledger-line">
            <span class="ledger-index">03</span>
            <div>
              <strong>Ask the real question</strong>
              <p>Ask the question and see how the people around it may react before anything goes live.</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <main class="main-content">
      <section ref="dashboardRef" class="intake-stage">
        <aside class="intake-rail">
          <div class="rail-sticky">
            <span class="section-kicker">How It Works</span>
            <h2>One intake, five live stages.</h2>
            <p class="section-intro">
              JunoFish helps you turn a company question into something you can explore. The setup
              stays simple so you can get to the useful part faster.
            </p>

            <div class="stage-list">
              <div class="stage-item">
                <span class="stage-index">01</span>
                <div>
                  <h3>Graph Construction</h3>
                  <p>Pull out the key people, groups, and relationships behind the company story.</p>
                </div>
              </div>
              <div class="stage-item">
                <span class="stage-index">02</span>
                <div>
                  <h3>Environment Setup</h3>
                  <p>Set up the people, channels, and conditions that shape the scenario.</p>
                </div>
              </div>
              <div class="stage-item">
                <span class="stage-index">03</span>
                <div>
                  <h3>Simulation Run</h3>
                  <p>Watch how reactions build, spread, and change over time.</p>
                </div>
              </div>
              <div class="stage-item">
                <span class="stage-index">04</span>
                <div>
                  <h3>Report Generation</h3>
                  <p>Get a clearer read on likely outcomes, tradeoffs, and risks.</p>
                </div>
              </div>
              <div class="stage-item">
                <span class="stage-index">05</span>
                <div>
                  <h3>Deep Interaction</h3>
                  <p>Go back in, ask follow-up questions, and explore what happened in more detail.</p>
                </div>
              </div>
            </div>

            <div class="rail-signals">
              <div class="signal-row">
                <span>Input</span>
                <strong>Website and docs together</strong>
              </div>
              <div class="signal-row">
                <span>Approach</span>
                <strong>Build the picture before the answer</strong>
              </div>
              <div class="signal-row">
                <span>Output</span>
                <strong>Clear recommendation plus saved project</strong>
              </div>
            </div>
          </div>
        </aside>

        <section class="console-stage" aria-label="JunoFish intake console">
          <div class="console-frame">
            <div class="console-head">
              <div>
                <span class="console-kicker">Intake Console</span>
                <h2>Give JunoFish the basics.</h2>
              </div>
              <span class="console-state">
                {{ consoleStateLabel }}
              </span>
            </div>

            <div class="console-section">
              <div class="console-header">
                <span class="console-label">01 / Company Website URL</span>
                <span class="console-meta">Optional if you upload source documents</span>
              </div>

              <div class="input-shell">
                <input
                  v-model="formData.companyWebsiteUrl"
                  class="text-input"
                  type="url"
                  placeholder="https://www.example.com/"
                  :disabled="loading"
                  @blur="urlTouched = true"
                />
              </div>

              <p class="field-hint">
                Use the main company website. JunoFish pulls in the public story and combines it
                with anything you upload here.
              </p>

              <p v-if="showCompanyWebsiteUrlError" class="field-error">
                {{ companyWebsiteUrlError }}
              </p>
            </div>

            <div class="console-rule">
              <span>Source Material</span>
            </div>

            <div class="console-section">
              <div class="console-header">
                <span class="console-label">02 / Documents</span>
                <span class="console-meta">PDF, MD, TXT</span>
              </div>

              <div
                class="upload-zone"
                :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
                @dragover.prevent="handleDragOver"
                @dragleave.prevent="handleDragLeave"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <input
                  ref="fileInput"
                  type="file"
                  multiple
                  accept=".pdf,.md,.txt"
                  @change="handleFileSelect"
                  style="display: none"
                  :disabled="loading"
                />

                <div v-if="files.length === 0" class="upload-placeholder">
                  <div class="upload-icon">↑</div>
                  <div class="upload-title">Drop documents here</div>
                  <div class="upload-hint">or click to pull from your filesystem</div>
                </div>

                <div v-else class="file-list">
                  <div v-for="(file, index) in files" :key="`${file.name}-${index}`" class="file-item">
                    <span class="file-pill">{{ file.name.split('.').pop()?.toUpperCase() || 'FILE' }}</span>
                    <span class="file-name">{{ file.name }}</span>
                    <button @click.stop="removeFile(index)" class="remove-btn" type="button">×</button>
                  </div>
                </div>
              </div>
            </div>

            <div class="console-rule">
              <span>Decision Prompt</span>
            </div>

            <div class="console-section">
              <div class="console-header">
                <span class="console-label">03 / Strategy Question</span>
                <span class="console-meta">What do you want help thinking through?</span>
              </div>

              <div class="input-shell textarea-shell">
                <textarea
                  v-model="formData.simulationRequirement"
                  class="code-input"
                  placeholder="// Describe the decision, risk, or opportunity you want to explore"
                  rows="7"
                  :disabled="loading"
                ></textarea>
                <div class="model-badge">Engine / JunoFish-V1.0</div>
              </div>

              <div class="prompt-presets">
                <button
                  v-for="preset in suggestedPrompts"
                  :key="preset.title"
                  type="button"
                  class="preset-btn"
                  @click="applySuggestedPrompt(preset.prompt)"
                >
                  <span class="preset-title">{{ preset.title }}</span>
                  <span class="preset-description">{{ preset.description }}</span>
                </button>
              </div>
            </div>

            <div class="console-footer">
              <div class="launch-copy">
                <span>Launch path</span>
                <strong>{{ launchSupportCopy }}</strong>
              </div>

              <div class="launch-actions">
                <p v-if="error" class="field-error submit-error">{{ error }}</p>
                <button class="start-engine-btn" @click="startSimulation" :disabled="!canSubmit || loading">
                  <span>{{ launchLabel }}</span>
                  <span class="btn-arrow">→</span>
                </button>
              </div>
            </div>
          </div>
        </section>
      </section>

      <section v-if="session.data?.user" ref="archiveRef" class="archive-stage">
        <div class="archive-header">
          <span class="section-kicker">Past Work</span>
          <h2>Reopen earlier projects and reports.</h2>
          <p>
            Signed in as {{ session.data.user.name }}. Jump back into earlier work and pick up
            where you left off.
          </p>
        </div>

        <HistoryDatabase />
      </section>

      <section v-else class="archive-locked">
        <div class="archive-locked-copy">
          <span class="section-kicker">Past Work</span>
          <h2>You can explore the page without signing in.</h2>
          <p>
            Sign in only when you want to reopen earlier projects, save new work, or move into the
            full app experience.
          </p>
        </div>

        <button class="archive-locked-btn" @click="router.push('/auth')">Sign in to view past work</button>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import heroScene from '../assets/hero/juno-fish-original.jpg'
import HistoryDatabase from '../components/HistoryDatabase.vue'
import { authClient } from '../lib/auth-client'
import { setPendingUpload } from '../store/pendingUpload'

const router = useRouter()
const session = authClient.useSession()

const suggestedPrompts = [
  {
    title: 'Next Best Move',
    description: 'Recommend the strongest direction for the next 12 months.',
    prompt:
      'Based on the company website and uploaded documents, suggest the three strongest directions for the next 12 months. Explain how customers, partners, and the market may react, then recommend the best path with reasons, risks, and assumptions.'
  },
  {
    title: 'Growth Focus',
    description: 'Compare the biggest growth paths and recommend one.',
    prompt:
      'Using the company website and uploaded documents, compare three growth options: entering a new market, launching a new product, or sharpening positioning in the current market. Recommend the best option and explain the tradeoffs and execution risks.'
  },
  {
    title: 'Positioning Check',
    description: 'Find out whether the current message should stay or change.',
    prompt:
      'Review the positioning shown on the website and in the uploaded documents. Show how customers, partners, and internal teams might react to a repositioning, then recommend whether the company should stay the course, refine it, or make a bigger change.'
  }
]

const formData = ref({
  companyWebsiteUrl: '',
  simulationRequirement: ''
})

const files = ref([])
const loading = ref(false)
const error = ref('')
const isDragOver = ref(false)
const urlTouched = ref(false)
const fileInput = ref(null)
const dashboardRef = ref(null)
const archiveRef = ref(null)

const companyWebsiteUrlError = computed(() => validateCompanyWebsiteUrl(formData.value.companyWebsiteUrl))
const showCompanyWebsiteUrlError = computed(() => urlTouched.value && Boolean(companyWebsiteUrlError.value))
const canSubmit = computed(() => {
  return formData.value.simulationRequirement.trim() !== '' && !companyWebsiteUrlError.value
})

const accessLabel = computed(() => (session.data?.user ? 'Open Archive' : 'Sign In'))
const consoleStateLabel = computed(() => {
  return session.data?.user ? 'Signed in / ready to start' : 'Browse now / sign in when you launch'
})
const launchLabel = computed(() => {
  if (loading.value) return 'Preparing intake...'
  return session.data?.user ? 'Launch JunoFish' : 'Launch and sign in'
})
const launchSupportCopy = computed(() => {
  return session.data?.user
    ? 'You are signed in. Start here and continue straight into your project.'
    : 'We will hold your setup, then ask you to sign in before opening the project.'
})

const isIpv4 = (hostname) => /^(?:\d{1,3}\.){3}\d{1,3}$/.test(hostname)

const isPrivateOrReservedIpv4 = (hostname) => {
  const parts = hostname.split('.').map(Number)
  if (parts.length !== 4 || parts.some((part) => Number.isNaN(part) || part < 0 || part > 255)) {
    return true
  }
  if (parts[0] === 10) return true
  if (parts[0] === 127) return true
  if (parts[0] === 169 && parts[1] === 254) return true
  if (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) return true
  if (parts[0] === 192 && parts[1] === 168) return true
  if (parts[0] === 0) return true
  return false
}

const validateCompanyWebsiteUrl = (rawUrl) => {
  const trimmed = (rawUrl || '').trim()
  if (!trimmed) {
    return files.value.length === 0
      ? 'Provide a company website URL or upload at least one document.'
      : ''
  }

  let parsed
  try {
    parsed = new URL(trimmed)
  } catch {
    return 'Please enter a valid URL.'
  }

  if (!['http:', 'https:'].includes(parsed.protocol)) {
    return 'Only public HTTP/HTTPS URLs are supported.'
  }
  if (parsed.username || parsed.password) {
    return 'Credentials in the URL are not allowed.'
  }
  if (parsed.port) {
    return 'Use the root domain URL without a custom port.'
  }
  if (parsed.search || parsed.hash) {
    return 'Use only the root domain URL without query or hash parameters.'
  }
  if (parsed.pathname && parsed.pathname !== '/') {
    return 'Use a single root domain URL, not a specific page path.'
  }

  const hostname = parsed.hostname.toLowerCase()
  if (!hostname || !hostname.includes('.') || hostname.endsWith('.')) {
    return 'Please enter a valid public root domain.'
  }
  if (hostname === 'localhost' || hostname.endsWith('.local') || hostname.endsWith('.internal')) {
    return 'Local or private hostnames are not allowed.'
  }
  if (hostname.includes(':')) {
    return 'Please use a public domain instead of an IP address.'
  }
  if (isIpv4(hostname) && isPrivateOrReservedIpv4(hostname)) {
    return 'Private or reserved IP addresses are not allowed.'
  }
  if (isIpv4(hostname)) {
    return 'Please use a public company domain rather than an IP address.'
  }

  return ''
}

const triggerFileInput = () => {
  if (!loading.value) {
    fileInput.value?.click()
  }
}

const handleFileSelect = (event) => {
  addFiles(Array.from(event.target.files || []))
}

const handleDragOver = () => {
  if (!loading.value) {
    isDragOver.value = true
  }
}

const handleDragLeave = () => {
  isDragOver.value = false
}

const handleDrop = (event) => {
  isDragOver.value = false
  if (loading.value) return
  addFiles(Array.from(event.dataTransfer.files || []))
}

const addFiles = (newFiles) => {
  const validFiles = newFiles.filter((file) => {
    const ext = file.name?.split('.').pop()?.toLowerCase()
    return ['pdf', 'md', 'txt'].includes(ext)
  })

  const seen = new Set(files.value.map((file) => `${file.name}:${file.size}:${file.lastModified}`))
  const nextFiles = [...files.value]

  validFiles.forEach((file) => {
    const key = `${file.name}:${file.size}:${file.lastModified}`
    if (!seen.has(key)) {
      seen.add(key)
      nextFiles.push(file)
    }
  })

  files.value = nextFiles
}

const removeFile = (index) => {
  files.value = files.value.filter((_, currentIndex) => currentIndex !== index)
}

const applySuggestedPrompt = (prompt) => {
  formData.value.simulationRequirement = prompt
}

const scrollToSetup = () => {
  dashboardRef.value?.scrollIntoView({
    behavior: 'smooth',
    block: 'start'
  })
}

const handleAccess = () => {
  if (session.data?.user) {
    archiveRef.value?.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    })
    return
  }

  router.push('/auth')
}

const startSimulation = () => {
  urlTouched.value = true
  error.value = ''

  if (!canSubmit.value || loading.value) {
    if (!formData.value.simulationRequirement.trim()) {
      error.value = 'Add the question you want to explore before launching.'
    }
    return
  }

  setPendingUpload(
    files.value,
    formData.value.simulationRequirement.trim(),
    formData.value.companyWebsiteUrl.trim()
  )

  router.push({
    name: 'Process',
    params: { projectId: 'new' }
  })
}
</script>

<style scoped>
.home-container {
  --ink: #071017;
  --ink-soft: rgba(7, 16, 23, 0.72);
  --paper: #f3eee6;
  --paper-warm: #e7ddd0;
  --sand: #f7f2eb;
  --orange: #ff7a3d;
  --orange-soft: rgba(255, 122, 61, 0.12);
  --line: rgba(7, 16, 23, 0.14);
  min-height: 100vh;
  background: linear-gradient(180deg, #10181e 0%, #efe7dc 42%, #f7f2eb 100%);
  color: var(--ink);
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
}

.hero-stage {
  position: relative;
  min-height: 100svh;
  overflow: hidden;
  color: #ffffff;
  background: #091117;
}

.hero-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center center;
  transform: scale(1.05);
  animation: heroDrift 18s ease-in-out infinite alternate;
}

.hero-film {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(6, 12, 16, 0.9) 0%, rgba(6, 12, 16, 0.72) 38%, rgba(6, 12, 16, 0.34) 72%, rgba(6, 12, 16, 0.18) 100%),
    linear-gradient(180deg, rgba(6, 12, 16, 0.18) 0%, rgba(6, 12, 16, 0.12) 100%);
}

.hero-grain {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
  background-size: 120px 120px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.2), rgba(0, 0, 0, 0.85));
  opacity: 0.25;
}

.navbar,
.hero-layout,
.main-content {
  width: min(1480px, calc(100% - 48px));
  margin: 0 auto;
  position: relative;
  z-index: 2;
}

.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 26px;
}

.nav-brand {
  display: grid;
  gap: 4px;
}

.nav-mark,
.nav-cta,
.hero-kicker,
.ledger-index,
.section-kicker,
.console-kicker,
.console-label,
.console-meta,
.model-badge,
.signal-row span,
.file-pill,
.archive-locked-btn,
.hero-primary-btn,
.hero-secondary-btn {
  font-family: 'JetBrains Mono', monospace;
}

.nav-mark {
  font-size: 1rem;
  font-weight: 800;
  letter-spacing: 0.24em;
}

.nav-meta {
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.62);
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.nav-cta {
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.06);
  color: #ffffff;
  padding: 12px 16px;
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  backdrop-filter: blur(14px);
}

.nav-cta {
  cursor: pointer;
}

.hero-layout {
  min-height: calc(100svh - 94px);
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(280px, 0.56fr);
  align-items: end;
  gap: 56px;
  padding-bottom: 56px;
}

.hero-copy {
  max-width: 760px;
  padding-top: 80px;
}

.hero-copy > * {
  opacity: 0;
  transform: translateY(22px);
  animation: heroReveal 0.85s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.hero-copy > *:nth-child(1) {
  animation-delay: 0.08s;
}

.hero-copy > *:nth-child(2) {
  animation-delay: 0.16s;
}

.hero-copy > *:nth-child(3) {
  animation-delay: 0.24s;
}

.hero-copy > *:nth-child(4) {
  animation-delay: 0.32s;
}

.hero-copy > *:nth-child(5) {
  animation-delay: 0.4s;
}

.hero-copy > *:nth-child(6) {
  animation-delay: 0.48s;
}

.hero-kicker {
  margin-bottom: 18px;
  font-size: 0.78rem;
  letter-spacing: 0.14em;
  color: rgba(255, 255, 255, 0.78);
}

.hero-brand {
  font-size: clamp(4.2rem, 11vw, 8.6rem);
  line-height: 0.9;
  letter-spacing: -0.06em;
}

.hero-headline {
  max-width: 660px;
  margin-top: 20px;
  font-size: clamp(1.6rem, 3.6vw, 3rem);
  line-height: 1.02;
  letter-spacing: -0.04em;
}

.hero-body {
  max-width: 560px;
  margin-top: 22px;
  font-size: 1.05rem;
  line-height: 1.75;
  color: rgba(255, 255, 255, 0.8);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}

.hero-primary-btn,
.hero-secondary-btn {
  border: 0;
  padding: 14px 20px;
  font-size: 0.82rem;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: transform 0.22s ease, background 0.22s ease, border-color 0.22s ease;
}

.hero-primary-btn {
  background: var(--orange);
  color: #111111;
}

.hero-secondary-btn {
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.18);
}

.hero-primary-btn:hover,
.hero-secondary-btn:hover,
.nav-cta:hover,
.archive-locked-btn:hover,
.start-engine-btn:hover {
  transform: translateY(-2px);
}

.hero-footnote {
  max-width: 620px;
  margin-top: 18px;
  font-size: 0.92rem;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.65);
}

.hero-ledger {
  display: grid;
  gap: 18px;
  align-self: end;
  padding-bottom: 10px;
}

.ledger-line {
  display: grid;
  grid-template-columns: 42px 1fr;
  gap: 16px;
  padding-top: 18px;
  border-top: 1px solid rgba(255, 255, 255, 0.18);
  opacity: 0;
  transform: translateY(22px);
  animation: heroReveal 0.85s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.ledger-line:nth-child(1) {
  animation-delay: 0.38s;
}

.ledger-line:nth-child(2) {
  animation-delay: 0.48s;
}

.ledger-line:nth-child(3) {
  animation-delay: 0.58s;
}

.ledger-index {
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.62);
}

.ledger-line strong {
  display: block;
  font-size: 0.96rem;
}

.ledger-line p {
  margin-top: 6px;
  font-size: 0.92rem;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.72);
}

.main-content {
  padding-top: 48px;
  padding-bottom: 88px;
}

.intake-stage {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 48px;
  align-items: start;
}

.rail-sticky {
  position: sticky;
  top: 28px;
  display: grid;
  gap: 24px;
}

.section-kicker {
  display: inline-flex;
  color: var(--orange);
  font-size: 0.76rem;
  letter-spacing: 0.14em;
}

.intake-rail h2,
.archive-header h2,
.archive-locked h2,
.console-head h2 {
  font-size: clamp(2.1rem, 4vw, 3.4rem);
  line-height: 0.96;
  letter-spacing: -0.05em;
}

.section-intro,
.archive-header p,
.archive-locked p {
  max-width: 520px;
  color: var(--ink-soft);
  line-height: 1.72;
}

.stage-list {
  display: grid;
  gap: 14px;
}

.stage-item {
  display: grid;
  grid-template-columns: 52px 1fr;
  gap: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
  transition: transform 0.24s ease, border-color 0.24s ease;
}

.stage-item:hover {
  transform: translateX(6px);
  border-color: rgba(255, 122, 61, 0.38);
}

.stage-index {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  color: var(--orange);
}

.stage-item h3 {
  font-size: 1rem;
}

.stage-item p {
  margin-top: 5px;
  color: var(--ink-soft);
  line-height: 1.58;
}

.rail-signals {
  display: grid;
  gap: 12px;
  padding-top: 4px;
}

.signal-row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px 18px;
  padding-top: 12px;
  border-top: 1px solid rgba(7, 16, 23, 0.08);
}

.signal-row span {
  font-size: 0.75rem;
  letter-spacing: 0.12em;
  color: rgba(7, 16, 23, 0.48);
}

.signal-row strong {
  font-size: 0.95rem;
}

.console-frame {
  padding: 30px;
  border: 1px solid rgba(7, 16, 23, 0.08);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(248, 242, 234, 0.96)),
    radial-gradient(circle at top right, rgba(255, 122, 61, 0.08), transparent 28%);
  box-shadow: 0 28px 80px rgba(7, 16, 23, 0.08);
}

.console-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  padding-bottom: 18px;
  border-bottom: 1px solid rgba(7, 16, 23, 0.08);
}

.console-kicker {
  display: inline-flex;
  margin-bottom: 10px;
  font-size: 0.76rem;
  letter-spacing: 0.14em;
  color: var(--orange);
}

.console-state {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.74rem;
  letter-spacing: 0.08em;
  color: rgba(7, 16, 23, 0.5);
  text-transform: uppercase;
}

.console-section {
  display: grid;
  gap: 12px;
  padding: 24px 0;
}

.console-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
}

.console-label {
  font-size: 0.78rem;
  letter-spacing: 0.12em;
  color: rgba(7, 16, 23, 0.86);
}

.console-meta {
  font-size: 0.74rem;
  letter-spacing: 0.08em;
  color: rgba(7, 16, 23, 0.46);
}

.console-rule {
  display: flex;
  align-items: center;
  gap: 16px;
  color: rgba(7, 16, 23, 0.42);
}

.console-rule::before,
.console-rule::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(7, 16, 23, 0.08);
}

.console-rule span {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.input-shell {
  border: 1px solid rgba(7, 16, 23, 0.1);
  background: rgba(255, 255, 255, 0.78);
}

.text-input,
.code-input {
  width: 100%;
  border: 0;
  background: transparent;
  padding: 18px 18px 16px;
  font: inherit;
  color: var(--ink);
  outline: none;
}

.text-input {
  font-size: 1rem;
}

.code-input {
  min-height: 188px;
  resize: vertical;
  line-height: 1.65;
}

.textarea-shell {
  position: relative;
}

.model-badge {
  position: absolute;
  right: 16px;
  bottom: 14px;
  font-size: 0.7rem;
  letter-spacing: 0.08em;
  color: rgba(7, 16, 23, 0.42);
}

.field-hint {
  max-width: 680px;
  color: var(--ink-soft);
  line-height: 1.6;
}

.field-error {
  color: #b12b00;
  line-height: 1.55;
}

.upload-zone {
  min-height: 180px;
  display: grid;
  place-items: center;
  border: 1px dashed rgba(7, 16, 23, 0.18);
  background: rgba(255, 255, 255, 0.54);
  cursor: pointer;
  transition: border-color 0.22s ease, background 0.22s ease, transform 0.22s ease;
}

.upload-zone:hover,
.upload-zone.drag-over {
  border-color: rgba(255, 122, 61, 0.42);
  background: rgba(255, 248, 242, 0.92);
  transform: translateY(-1px);
}

.upload-zone.has-files {
  place-items: stretch;
}

.upload-placeholder {
  display: grid;
  gap: 8px;
  justify-items: center;
  padding: 22px;
  text-align: center;
}

.upload-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(7, 16, 23, 0.12);
  font-family: 'JetBrains Mono', monospace;
}

.upload-title {
  font-size: 0.98rem;
  font-weight: 600;
}

.upload-hint {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.76rem;
  color: rgba(7, 16, 23, 0.5);
}

.file-list {
  display: grid;
  gap: 10px;
  padding: 14px;
}

.file-item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(7, 16, 23, 0.08);
  background: rgba(255, 255, 255, 0.86);
}

.file-pill {
  display: inline-flex;
  padding: 5px 8px;
  background: rgba(255, 122, 61, 0.1);
  color: #9b3f16;
  font-size: 0.68rem;
  letter-spacing: 0.08em;
}

.file-name {
  min-width: 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remove-btn {
  border: 0;
  background: transparent;
  color: rgba(7, 16, 23, 0.5);
  font-size: 1.1rem;
  cursor: pointer;
}

.prompt-presets {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.preset-btn {
  display: grid;
  gap: 4px;
  padding: 14px;
  border: 1px solid rgba(7, 16, 23, 0.08);
  background: rgba(255, 255, 255, 0.62);
  text-align: left;
  cursor: pointer;
  transition: transform 0.22s ease, border-color 0.22s ease, background 0.22s ease;
}

.preset-btn:hover {
  transform: translateY(-2px);
  border-color: rgba(255, 122, 61, 0.32);
  background: rgba(255, 248, 242, 0.96);
}

.preset-title {
  font-size: 0.76rem;
  letter-spacing: 0.08em;
}

.preset-description {
  color: var(--ink-soft);
  line-height: 1.5;
}

.console-footer {
  display: grid;
  grid-template-columns: minmax(0, 0.72fr) minmax(0, 1fr);
  gap: 18px;
  padding-top: 24px;
  border-top: 1px solid rgba(7, 16, 23, 0.08);
}

.launch-copy {
  display: grid;
  gap: 8px;
}

.launch-copy span {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.74rem;
  letter-spacing: 0.12em;
  color: rgba(7, 16, 23, 0.48);
}

.launch-copy strong {
  font-size: 0.98rem;
  line-height: 1.55;
}

.launch-actions {
  display: grid;
  gap: 10px;
}

.submit-error {
  margin: 0;
}

.start-engine-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  border: 0;
  padding: 18px 20px;
  background: linear-gradient(135deg, #071017 0%, #183446 100%);
  color: #ffffff;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.84rem;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: transform 0.22s ease, opacity 0.22s ease;
}

.start-engine-btn:disabled {
  opacity: 0.58;
  cursor: not-allowed;
}

.btn-arrow {
  font-size: 1rem;
}

.archive-stage,
.archive-locked {
  margin-top: 72px;
}

.archive-header {
  display: grid;
  gap: 16px;
  margin-bottom: 18px;
}

.archive-locked {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 28px;
  padding-top: 22px;
  border-top: 1px solid rgba(7, 16, 23, 0.08);
}

.archive-locked-copy {
  display: grid;
  gap: 16px;
}

.archive-locked-btn {
  border: 0;
  padding: 15px 18px;
  background: #111111;
  color: #ffffff;
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  cursor: pointer;
  white-space: nowrap;
}

@keyframes heroReveal {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes heroDrift {
  0% {
    transform: scale(1.05) translate3d(0, 0, 0);
  }
  100% {
    transform: scale(1.1) translate3d(-1.5%, 1%, 0);
  }
}

@media (max-width: 1100px) {
  .hero-layout,
  .intake-stage,
  .console-footer,
  .archive-locked {
    grid-template-columns: 1fr;
  }

  .hero-layout {
    align-items: end;
    gap: 32px;
  }

  .hero-ledger {
    max-width: 520px;
  }

  .rail-sticky {
    position: static;
  }

  .archive-locked {
    align-items: start;
  }
}

@media (max-width: 820px) {
  .navbar,
  .hero-layout,
  .main-content {
    width: min(100%, calc(100% - 32px));
  }

  .navbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .hero-stage {
    min-height: auto;
    padding-bottom: 34px;
  }

  .hero-layout {
    min-height: auto;
    padding-top: 44px;
    padding-bottom: 12px;
  }

  .hero-copy {
    padding-top: 12px;
  }

  .hero-brand {
    font-size: clamp(3.3rem, 18vw, 5.4rem);
  }

  .hero-actions,
  .nav-actions {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }

  .console-head,
  .console-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .prompt-presets {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .console-frame {
    padding: 22px 18px;
  }

  .stage-item {
    grid-template-columns: 40px 1fr;
  }

  .file-item {
    grid-template-columns: 1fr auto;
  }

  .file-pill {
    display: none;
  }
}
</style>
