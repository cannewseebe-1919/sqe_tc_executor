import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    proxy: {
      '/api': {
        target: 'http://localhost:9000',
        changeOrigin: true,
        ws: true,
      },
      '/auth': {
        target: 'http://localhost:9000',
        changeOrigin: true,
      },
      '/screenshots': {
        target: 'http://localhost:9000',
        changeOrigin: true,
      },
    },
  },
})
