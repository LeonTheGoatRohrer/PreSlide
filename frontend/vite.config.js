import {defineConfig} from 'vite'
import vue from '@vitejs/plugin-vue'
// PRESLIDE_API_PORT lets the dev server talk to an API on another port (default: scripts/start.ps1 uses 8000).
const api = 'http://127.0.0.1:' + (process.env.PRESLIDE_API_PORT || 8000)
export default defineConfig({plugins: [vue()], server: {proxy: {'/api': api}}, build: {chunkSizeWarningLimit: 1600}})
