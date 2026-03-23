import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import dotenv from 'dotenv'
import Database from 'better-sqlite3'
import { betterAuth } from 'better-auth'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const rootDir = path.resolve(__dirname, '..')

dotenv.config({ path: path.join(rootDir, '.env') })
dotenv.config()

if (!process.env.BETTER_AUTH_SECRET) {
  throw new Error('BETTER_AUTH_SECRET is required to start the auth service')
}

const authPort = process.env.AUTH_SERVICE_PORT || '5002'
const defaultFrontendOrigin = process.env.FRONTEND_ORIGIN || 'http://localhost:3000'
const configuredOrigins = process.env.AUTH_TRUSTED_ORIGINS
  ?.split(',')
  .map((origin) => origin.trim())
  .filter(Boolean)

const trustedOrigins = configuredOrigins?.length
  ? configuredOrigins
  : [defaultFrontendOrigin, 'http://127.0.0.1:3000']

const dataDir = path.resolve(rootDir, 'data')
fs.mkdirSync(dataDir, { recursive: true })

const databasePath = process.env.AUTH_DB_PATH || path.join(dataDir, 'auth.db')
const database = new Database(databasePath)

export const auth = betterAuth({
  database,
  secret: process.env.BETTER_AUTH_SECRET,
  baseURL: process.env.BETTER_AUTH_URL || `http://localhost:${authPort}`,
  trustedOrigins,
  emailAndPassword: {
    enabled: true
  }
})

export const authConfig = {
  authPort,
  trustedOrigins
}
