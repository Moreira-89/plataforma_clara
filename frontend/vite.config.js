import { defineConfig } from 'vite'

// A URL do backend entra por variável de ambiente (VITE_API_URL) e é lida no
// código com import.meta.env. Em desenvolvimento, o proxy abaixo evita CORS:
// o browser chama /api no mesmo host e o Vite repassa para o backend local.
export default defineConfig({
  server: {
    port: 5173,
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
