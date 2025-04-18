import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_VERSION = import.meta.env.VITE_API_VERSION || 'v1'

// Ensure we're using port 8000 for the API
const apiUrl = API_URL.replace(':5173', ':8000');

// Check if API_URL already contains '/api'
const baseUrlPath = apiUrl.endsWith('/api') ? `${apiUrl}/${API_VERSION}` : `${apiUrl}/api/${API_VERSION}`;

export const axiosInstance = axios.create({
  baseURL: baseUrlPath,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true // Enable sending cookies and auth headers
})

// Add request interceptor to add auth token
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    console.log('🔄 Axios Request:', {
      url: config.url,
      method: config.method,
      headers: config.headers,
      baseURL: config.baseURL,
      fullUrl: `${config.baseURL}${config.url}`
    })
    return config
  },
  (error) => {
    console.error('❌ Axios Request Error:', error)
    return Promise.reject(error)
  }
)

// Add response interceptor to handle errors
axiosInstance.interceptors.response.use(
  (response) => {
    console.log('✅ Axios Response:', {
      status: response.status,
      data: response.data,
      headers: response.headers
    })
    return response
  },
  (error) => {
    console.error('❌ Axios Response Error:', {
      status: error.response?.status,
      data: error.response?.data,
      headers: error.response?.headers,
      config: {
        url: error.config?.url,
        method: error.config?.method,
        baseURL: error.config?.baseURL,
        headers: error.config?.headers,
        fullUrl: `${error.config?.baseURL}${error.config?.url}`
      }
    })

    if (error.response?.status === 401 || error.response?.status === 403) {
      // Clear token and redirect to login on auth errors
      console.log('🔒 Authentication error detected, clearing token')
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)