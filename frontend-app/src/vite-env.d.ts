/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MARKETING_SITE_URL: string
  readonly VITE_USE_MOCKS: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
