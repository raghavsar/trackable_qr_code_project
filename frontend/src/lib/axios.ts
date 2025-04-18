import axios, { AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios'

interface CustomAxiosRequestConfig extends InternalAxiosRequestConfig {
  retryCount: number;
}

// Create axios instance with default config
// Check if API_URL already contains '/api'
const baseUrl = typeof __API_URL__ === 'string' && __API_URL__.endsWith('/api')
  ? __API_URL__
  : `${__API_URL__}/api`;

export const api = axios.create({
  baseURL: baseUrl,
  withCredentials: true,
  timeout: 15000, // 15 second timeout
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
})

// Retry configuration
const MAX_RETRIES = 3
const RETRY_DELAY = 1000 // 1 second

// Add request interceptor
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('token')

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  // Convert to CustomAxiosRequestConfig and initialize retryCount
  const customConfig = config as CustomAxiosRequestConfig
  customConfig.retryCount = 0

  return customConfig
})

// Add response interceptor
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const config = error.config as CustomAxiosRequestConfig | undefined
    if (!config) {
      return Promise.reject(error)
    }

    // Initialize retryCount if not set
    config.retryCount = config.retryCount || 0

    // If we've already retried maximum times, throw error
    if (config.retryCount >= MAX_RETRIES) {
      return Promise.reject(error)
    }

    // Handle specific error cases
    switch (error.response?.status) {
      case 401: {
        try {
          // Try to refresh token
          const refreshToken = localStorage.getItem('refresh_token')
          if (!refreshToken) {
            throw new Error('No refresh token available')
          }

          const response = await api.post('/v1/auth/refresh', {
            refresh_token: refreshToken
          })

          const { access_token, refresh_token: new_refresh_token } = response.data

          localStorage.setItem('token', access_token)
          localStorage.setItem('refresh_token', new_refresh_token)

          // Update token in config and retry
          config.headers.Authorization = `Bearer ${access_token}`
          return api.request(config)
        } catch (refreshError) {
          // Clear auth and redirect to login
          localStorage.clear()
          window.location.href = '/auth/login'
          return Promise.reject(error)
        }
      }
      case 408: // Request Timeout
      case 429: // Too Many Requests
      case 500: // Internal Server Error
      case 502: // Bad Gateway
      case 503: // Service Unavailable
      case 504: // Gateway Timeout
        // Increment retry count
        config.retryCount += 1

        // Wait for delay * retry count
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * config.retryCount))

        // Retry request
        return api.request(config)
    }

    return Promise.reject(error)
  }
)