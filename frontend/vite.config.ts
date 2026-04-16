import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const backendHttp = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'
const backendWs = backendHttp.replace(/^http/, 'ws')

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': backendHttp,
      '/ws': {
        target: backendWs,
        ws: true,
      },
      '/webrtc': backendHttp,
      '/websocket': {
        target: backendWs,
        ws: true,
      },
    },
  },
})
