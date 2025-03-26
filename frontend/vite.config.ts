import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  // Set the third parameter to '' to load all env regardless of the `VITE_` prefix.
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      host: '192.168.7.60',
      // allowedHosts: ['e032-14-97-193-22.ngrok-free.app'],
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false
        },
        '/analytics': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
          rewrite: (path) => `/api/v1${path}`
        }
      },
      cors: true,
      hmr: {
        host: '192.168.7.60'
      }
    },
    preview: {
      port: 5173,
      host: '192.168.7.60'
    },
    define: {
      // Expose env variables to your app
      __API_URL__: JSON.stringify(env.VITE_API_URL),
      __API_VERSION__: JSON.stringify(env.VITE_API_VERSION),
      __AUTH_COOKIE_NAME__: JSON.stringify(env.VITE_AUTH_COOKIE_NAME),
      __AUTH_COOKIE_EXPIRES__: JSON.stringify(env.VITE_AUTH_COOKIE_EXPIRES),
      __ENABLE_GOOGLE_AUTH__: env.VITE_ENABLE_GOOGLE_AUTH === 'true',
      __ENABLE_ANALYTICS__: env.VITE_ENABLE_ANALYTICS === 'true',
      // Add process definition
      'process.env': {}
    }
  }
}) 