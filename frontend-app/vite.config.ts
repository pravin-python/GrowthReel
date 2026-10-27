import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // In dev, the sibling FastAPI service runs on :8001. Proxying /api here
      // means the app always calls relative `/api/v1/...` paths, identically
      // in dev and prod (prod is expected to reverse-proxy /api to FastAPI too).
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/api/v1/ws': {
        target: 'ws://localhost:8001',
        ws: true,
      },
    },
  },
})
