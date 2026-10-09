import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

// Site de várias páginas: cada HTML da raiz é uma entrada do build.
const pagina = (nome) => fileURLToPath(new URL(`./${nome}.html`, import.meta.url))

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
    rollupOptions: {
      input: {
        index: pagina('index'),
        login: pagina('paginas/login'),
        cadastro: pagina('paginas/cadastro'),
        novoBloco: pagina('paginas/gestora/novo-bloco'),
      },
    },
  },
})
