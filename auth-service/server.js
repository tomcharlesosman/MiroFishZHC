import dotenv from 'dotenv'
import express from 'express'
import cors from 'cors'
import { fromNodeHeaders, toNodeHandler } from 'better-auth/node'

import { auth, authConfig } from './auth.js'

dotenv.config()

const app = express()

app.use(
  cors({
    origin: authConfig.trustedOrigins,
    credentials: true
  })
)

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'JunoFish Auth Service' })
})

app.get('/api/session', async (req, res) => {
  try {
    const session = await auth.api.getSession({
      headers: fromNodeHeaders(req.headers)
    })

    if (!session) {
      return res.status(401).json({ session: null, user: null })
    }

    return res.json(session)
  } catch (error) {
    console.error('Failed to fetch session', error)
    return res.status(500).json({ error: 'Failed to fetch session' })
  }
})

app.all('/api/auth/{*splat}', toNodeHandler(auth))
app.use(express.json())

app.listen(Number(authConfig.authPort), '0.0.0.0', () => {
  console.log(`JunoFish auth service listening on port ${authConfig.authPort}`)
})
