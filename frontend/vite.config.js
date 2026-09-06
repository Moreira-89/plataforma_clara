import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    port: 5173,
    // Proxy evita CORS em desenvolvimento.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (caminho) => caminho.replace(/^\/api/, ''),
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
