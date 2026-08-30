import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws':  { target: 'ws://localhost:8000',  ws: true },
    },
  },
  // Build to the standard Vite 'dist' output directory.
  //
  // IMPORTANT: do NOT change outDir to '../app/static'.
  // The Dockerfile copies frontend/dist → app/static in a multi-stage build.
  // Using a custom outDir that writes outside the WORKDIR breaks the
  // COPY --from=frontend-builder step because that path never exists in the
  // builder stage — it was the root cause of "frontend not showing" on every
  // Docker/Railway/Render/Fly deploy.
  build: { outDir: 'dist' },
})
