import { reactive, readonly } from 'vue'
import Privy, { LocalStorage, getUserEmbeddedEthereumWallet } from '@privy-io/js-sdk-core'

const privyAppId = import.meta.env.VITE_PRIVY_APP_ID
const privyClientId = import.meta.env.VITE_PRIVY_CLIENT_ID || undefined

const authState = reactive({
  ready: false,
  initializing: false,
  authenticated: false,
  user: null,
  accessToken: null,
  error: ''
})

const sessionState = reactive({
  data: null
})

let client = null
let initializePromise = null
let secureContextPromise = null

const embeddedWalletIframeId = 'privy-embedded-wallet-context'

const linkedAccounts = (user) => (Array.isArray(user?.linked_accounts) ? user.linked_accounts : [])

const getRawUser = (user) => user?.raw || user || null

const getPrimaryEmail = (user = authState.user) => {
  const rawUser = getRawUser(user)
  const emailAccount = linkedAccounts(rawUser).find((account) => account?.type === 'email')
  return emailAccount?.address || user?.email || ''
}

export const getPrimaryWalletAddress = (user = authState.user) => {
  const rawUser = getRawUser(user)
  const walletAccount = linkedAccounts(rawUser).find((account) => {
    return account?.type === 'wallet' || account?.type?.includes?.('wallet') || account?.address
  })

  return walletAccount?.address || user?.walletAddress || ''
}

export const getPrimaryUserLabel = (user = authState.user) => {
  if (user?.name) {
    return user.name
  }

  return getPrimaryEmail(user) || getPrimaryWalletAddress(user) || user?.id || 'Privy user'
}

const toSessionUser = (user) => {
  if (!user) {
    return null
  }

  const email = getPrimaryEmail(user)
  const walletAddress = getPrimaryWalletAddress(user)
  const shortWalletAddress = walletAddress ? `${walletAddress.slice(0, 6)}...${walletAddress.slice(-4)}` : ''
  const displayName = typeof user?.name === 'string' && user.name.trim()
    ? user.name.trim()
    : (email ? email.split('@')[0] : shortWalletAddress || user.id || 'JunoFish')

  return {
    id: user.id,
    name: displayName,
    email,
    walletAddress,
    raw: user
  }
}

const syncSessionState = (user, accessToken) => {
  authState.user = toSessionUser(user)
  authState.accessToken = accessToken || null
  authState.authenticated = Boolean(authState.user && accessToken)
  sessionState.data = authState.user ? { user: authState.user } : null
}

const clearAuthState = () => {
  syncSessionState(null, null)
}

const getClient = () => {
  if (client) {
    return client
  }

  if (!privyAppId) {
    throw new Error('Missing VITE_PRIVY_APP_ID. Set it before initializing Privy.')
  }

  client = new Privy({
    appId: privyAppId,
    clientId: privyClientId,
    storage: new LocalStorage()
  })

  return client
}

const getEmbeddedWalletIframe = (iframeUrl) => {
  if (typeof document === 'undefined') {
    throw new Error('Privy embedded wallets require a browser context.')
  }

  let iframe = document.getElementById(embeddedWalletIframeId)

  if (!(iframe instanceof HTMLIFrameElement)) {
    iframe = document.createElement('iframe')
    iframe.id = embeddedWalletIframeId
    iframe.title = 'Privy embedded wallet context'
    iframe.setAttribute('aria-hidden', 'true')
    iframe.tabIndex = -1
    Object.assign(iframe.style, {
      position: 'fixed',
      width: '0',
      height: '0',
      border: '0',
      opacity: '0',
      pointerEvents: 'none',
      inset: 'auto'
    })
    document.body.appendChild(iframe)
  }

  if (iframe.src !== iframeUrl) {
    iframe.dataset.privyReady = 'false'
  }

  return iframe
}

const waitForEmbeddedWalletIframe = async (iframe, iframeUrl) => {
  if (iframe.dataset.privyReady === 'true' && iframe.contentWindow) {
    return iframe
  }

  await new Promise((resolve, reject) => {
    const onLoad = () => {
      cleanup()
      iframe.dataset.privyReady = 'true'
      resolve()
    }
    const onError = () => {
      cleanup()
      reject(new Error('Failed to initialize the Privy embedded wallet context.'))
    }
    const cleanup = () => {
      iframe.removeEventListener('load', onLoad)
      iframe.removeEventListener('error', onError)
    }

    iframe.addEventListener('load', onLoad, { once: true })
    iframe.addEventListener('error', onError, { once: true })
    iframe.src = iframeUrl
  })

  if (!iframe.contentWindow) {
    throw new Error('Privy embedded wallet context did not expose a message channel.')
  }

  return iframe
}

const normalizeEmbeddedWalletMessage = (data) => {
  if (typeof data === 'string') {
    try {
      return JSON.parse(data)
    } catch (_error) {
      return null
    }
  }

  if (data && typeof data === 'object') {
    return data
  }

  return null
}

const ensureEmbeddedWalletSecureContext = async () => {
  if (typeof window === 'undefined') {
    throw new Error('Privy embedded wallets require a browser context.')
  }

  if (secureContextPromise) {
    return secureContextPromise
  }

  secureContextPromise = (async () => {
    const privy = getClient()
    const iframeUrl = privy.embeddedWallet.getURL()
    const iframe = getEmbeddedWalletIframe(iframeUrl)

    await waitForEmbeddedWalletIframe(iframe, iframeUrl)

    const poster = iframe.contentWindow

    if (!poster) {
      throw new Error('Privy embedded wallet context did not initialize correctly.')
    }

    privy.setMessagePoster(poster)

    if (window.__junofishPrivyEmbeddedWalletListener) {
      window.removeEventListener('message', window.__junofishPrivyEmbeddedWalletListener)
    }

    const listener = (event) => {
      const iframeElement = document.getElementById(embeddedWalletIframeId)

      if (!(iframeElement instanceof HTMLIFrameElement) || event.source !== iframeElement.contentWindow) {
        return
      }

      const payload = normalizeEmbeddedWalletMessage(event.data)

      if (!payload) {
        return
      }

      getClient().embeddedWallet.onMessage(payload)
    }

    window.addEventListener('message', listener)
    window.__junofishPrivyEmbeddedWalletListener = listener

    const connected = await privy.embeddedWallet.ping(5000).catch(() => false)

    if (!connected) {
      throw new Error('Privy embedded wallet context did not respond. Check your browser privacy settings and allowed domains.')
    }

    return iframe
  })().catch((error) => {
    secureContextPromise = null
    throw error
  })

  return secureContextPromise
}

const ensureEmbeddedWalletForAuthenticatedUser = async () => {
  const privy = getClient()
  const accessToken = await privy.getAccessToken()

  if (!accessToken) {
    clearAuthState()
    return null
  }

  const { user } = await privy.user.get()

  if (getUserEmbeddedEthereumWallet(user)) {
    syncSessionState(user, accessToken)
    return sessionState.data
  }

  await ensureEmbeddedWalletSecureContext()
  await privy.embeddedWallet.create({})

  return refreshSession()
}

export const getAuthState = () => readonly(authState)

export const initializeAuth = async () => {
  if (authState.ready) {
    return authState
  }

  if (initializePromise) {
    return initializePromise
  }

  authState.initializing = true

  initializePromise = (async () => {
    const privy = getClient()
    await privy.initialize()
    await refreshSession()
    authState.ready = true
    authState.error = ''
    return authState
  })()
    .catch((error) => {
      clearAuthState()
      authState.error = error?.message || 'Failed to initialize Privy.'
      throw error
    })
    .finally(() => {
      authState.initializing = false
      initializePromise = null
    })

  return initializePromise
}

export const refreshSession = async () => {
  const privy = getClient()

  try {
    const accessToken = await privy.getAccessToken()

    if (!accessToken) {
      clearAuthState()
      return null
    }

    const { user } = await privy.user.get()
    syncSessionState(user, accessToken)
    authState.error = ''

    return sessionState.data
  } catch (_error) {
    clearAuthState()
    return null
  }
}

export const getAccessToken = async () => {
  const privy = getClient()
  await initializeAuth()

  const accessToken = await privy.getAccessToken()

  if (!accessToken) {
    clearAuthState()
    return null
  }

  authState.accessToken = accessToken

  if (!authState.user) {
    await refreshSession()
  }

  return authState.accessToken
}

export const sendEmailCode = async (email) => {
  const privy = getClient()
  await initializeAuth()
  return privy.auth.email.sendCode(email.trim())
}

export const loginWithEmailCode = async (email, code) => {
  const privy = getClient()
  await initializeAuth()
  await privy.auth.email.loginWithCode(email.trim(), code.trim(), 'login-or-sign-up')
  return ensureEmbeddedWalletForAuthenticatedUser()
}

const getInjectedProvider = () => {
  if (typeof window === 'undefined' || !window.ethereum) {
    throw new Error('No injected Ethereum wallet found. Install MetaMask or another EVM wallet to continue.')
  }

  return window.ethereum
}

const detectWalletClientType = (provider) => {
  if (provider?.isMetaMask) return 'metamask'
  if (provider?.isBraveWallet) return 'brave_wallet'
  return 'unknown'
}

const buildWalletMetadata = (provider) => {
  if (provider?.isMetaMask) {
    return { name: 'MetaMask', id: 'metamask' }
  }

  if (provider?.isBraveWallet) {
    return { name: 'Brave Wallet', id: 'brave_wallet' }
  }

  return { name: 'Injected Wallet', id: 'injected-wallet' }
}

const buildExternalWallet = async (provider, address) => {
  const chainIdHex = await provider.request({ method: 'eth_chainId' })
  const chainId = Number.parseInt(chainIdHex, 16)

  if (!chainId) {
    throw new Error('Unable to determine the connected chain for this wallet.')
  }

  return {
    address,
    chainId: `eip155:${chainId}`,
    walletClientType: detectWalletClientType(provider),
    connectorType: 'injected',
    meta: buildWalletMetadata(provider)
  }
}

export const loginWithEthereumWallet = async () => {
  const privy = getClient()
  await initializeAuth()

  const provider = getInjectedProvider()
  const accounts = await provider.request({ method: 'eth_requestAccounts' })
  const address = accounts?.[0]

  if (!address) {
    throw new Error('No Ethereum account was returned by the wallet.')
  }

  const wallet = await buildExternalWallet(provider, address)
  const { message } = await privy.auth.siwe.init(wallet, window.location.host, window.location.origin)
  const signature = await provider.request({
    method: 'personal_sign',
    params: [message, address]
  })

  await privy.auth.siwe.loginWithSiwe(
    signature,
    wallet,
    message,
    'login-or-sign-up'
  )

  return ensureEmbeddedWalletForAuthenticatedUser()
}

export const logout = async () => {
  const privy = getClient()

  try {
    await initializeAuth()
    await privy.auth.logout(authState.user?.id ? { userId: authState.user.id } : undefined)
  } finally {
    clearAuthState()
    authState.ready = true
  }
}

export const authClient = {
  useSession() {
    return readonly(sessionState)
  },
  async getSession() {
    await initializeAuth()
    return { data: sessionState.data }
  },
  async signOut() {
    await logout()
  }
}
