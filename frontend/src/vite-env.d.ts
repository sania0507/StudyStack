/// <reference types="vite/client" />

// Where the three FastAPI services live. Set these in .env.local for
// development and in Vercel's project settings for production.
interface ImportMetaEnv {
  readonly VITE_AUTH_URL?: string
  readonly VITE_MAIN_URL?: string
  readonly VITE_ANALYTICS_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
