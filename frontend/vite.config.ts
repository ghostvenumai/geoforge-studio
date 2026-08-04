import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  preview: { host: '127.0.0.1', port: 4173 },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('@uiw') || id.includes('codemirror') || id.includes('@codemirror')) return 'editor'
          if (id.includes('@xyflow')) return 'flow'
          if (id.includes('recharts') || id.includes('d3-')) return 'charts'
          if (id.includes('@tanstack')) return 'data'
          return 'vendor'
        },
      },
    },
  },
})
