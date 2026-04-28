import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const rootDir = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        index: resolve(rootDir, 'index.html'),
        register: resolve(rootDir, 'register.html'),
        levels: resolve(rootDir, 'levels.html'),
        puzzle: resolve(rootDir, 'puzzle.html'),
      },
    },
  },
})
