import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      // Proxy requests starting with '/api' to your backend server
      '/api': {
        target: 'http://localhost:8000', // Replace with your backend server's URL and port
        changeOrigin: true, // Needed for virtual hosted sites
        rewrite: (path) => path.replace(/^\/api/, ''), // Remove the '/api' prefix when forwarding the request
      },
    },
  },
  optimizeDeps: {
    // Explicitly include ajv and the 2019-09 distribution
    include: ['ajv', 'ajv/dist/2019.js'],
  },
  build: {
    commonjsOptions: {
      // Ensure CommonJS modules are transformed properly
      include: [/node_modules/],
    },
  },
})
