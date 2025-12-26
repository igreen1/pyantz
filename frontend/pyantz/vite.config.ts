import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Proxy requests starting with '/api' to your backend server
      '/api': {
        target: 'http://localhost:8000', // Replace with your backend server's URL and port
        changeOrigin: true, // Needed for virtual hosted sites
        rewrite: (path) => path.replace(/^\/api/, ''), // Remove the '/api' prefix when forwarding the request
      },
    },
  },
})
