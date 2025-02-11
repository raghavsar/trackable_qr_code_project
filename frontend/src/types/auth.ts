import type { User } from './index'

export interface AuthResponse {
  user: User
  access_token: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
  full_name: string
}

export interface ProfileUpdateData {
  full_name?: string
  email?: string
  profile_picture?: string
  current_password?: string
  new_password?: string
}

export interface GoogleAuthResponse {
  auth_url: string
  state: string
}

export interface UpdateProfileData {
  full_name?: string
  email?: string
  profile_picture?: string
}

export interface UpdatePasswordData {
  current_password: string
  new_password: string
}

export interface AuthContextType {
  isAuthenticated: boolean
  user: User | null
  token: string | null
  loading: boolean
  isLoading: boolean
  setUser: (user: User) => void
  setToken: (token: string) => void
  logout: () => void
} 