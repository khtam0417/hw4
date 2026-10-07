import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The FastAPI backend (backend/main.py) serves /api and /media, on port 8000 by default
// (uvicorn main:app --reload --port 8000). Set BACKEND_PORT to use another port, for example
// BACKEND_PORT=8001 while 8000 is busy. Proxying keeps the browser on one origin, so the frontend
// can use paths like /api/products. Port 5174 avoids the lecture 10 project, which keeps 5173 busy.
const BACKEND_URL = `http://127.0.0.1:${process.env.BACKEND_PORT ?? '8000'}`

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': BACKEND_URL,
      '/media': BACKEND_URL,
    },
  },
})
