<template>
  <div v-if="session.data?.user" class="workspace-session">
    <div class="workspace-session__identity">
      <span class="workspace-session__avatar">{{ initials }}</span>
      <div class="workspace-session__copy">
        <span class="workspace-session__label">Signed in</span>
        <strong>{{ displayName }}</strong>
        <span class="workspace-session__email">{{ displayEmail }}</span>
      </div>
    </div>

    <button class="workspace-session__action" :disabled="isSigningOut" @click="handleSignOut">
      <span v-if="isSigningOut">Signing out...</span>
      <span v-else>Sign out</span>
    </button>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { authClient } from '../lib/auth-client'

const router = useRouter()
const session = authClient.useSession()
const isSigningOut = ref(false)

const displayName = computed(() => {
  const name = session.data?.user?.name?.trim()
  if (name) return name

  const email = session.data?.user?.email || ''
  return email.split('@')[0] || 'Workspace'
})

const displayEmail = computed(() => session.data?.user?.email || '')

const initials = computed(() => {
  const seed = displayName.value
  if (!seed) return 'JF'

  const letters = seed
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('')

  return letters || seed.slice(0, 2).toUpperCase()
})

const handleSignOut = async () => {
  isSigningOut.value = true

  try {
    await authClient.signOut()
    await router.push({ name: 'Home' })
  } finally {
    isSigningOut.value = false
  }
}
</script>

<style scoped>
.workspace-session {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  padding-left: 16px;
  border-left: 1px solid rgba(17, 24, 39, 0.1);
}

.workspace-session__identity {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.workspace-session__avatar {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #f6efe2 0%, #efe5d2 100%);
  color: #142033;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  flex-shrink: 0;
}

.workspace-session__copy {
  display: grid;
  gap: 1px;
  min-width: 0;
}

.workspace-session__label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #9f8f73;
}

.workspace-session__copy strong {
  font-size: 13px;
  font-weight: 700;
  color: #111827;
  line-height: 1.1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.workspace-session__email {
  font-size: 11px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
}

.workspace-session__action {
  border: 1px solid rgba(17, 24, 39, 0.12);
  border-radius: 999px;
  padding: 9px 12px;
  background: #ffffff;
  color: #111827;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.workspace-session__action:hover:not(:disabled) {
  background: #111827;
  border-color: #111827;
  color: #ffffff;
}

.workspace-session__action:disabled {
  opacity: 0.6;
  cursor: wait;
}

@media (max-width: 1380px) {
  .workspace-session__email {
    display: none;
  }
}

@media (max-width: 1220px) {
  .workspace-session__label {
    display: none;
  }

  .workspace-session__copy strong {
    max-width: 128px;
  }
}

@media (max-width: 1120px) {
  .workspace-session {
    padding-left: 12px;
  }

  .workspace-session__copy {
    display: none;
  }
}
</style>
