import { createAuthClient } from 'better-auth/vue'

export const authClient = createAuthClient({
  baseURL: import.meta.env.VITE_AUTH_BASE_URL || window.location.origin,
  fetchOptions: {
    credentials: 'include'
  }
})
