export interface User {
  _id: string
  email: string
  full_name: string
  is_active: boolean
  is_superuser: boolean
  profile_picture?: string | null
  auth_provider: "email" | "google"
  created_at: string
  updated_at: string
  password_hash?: string | null
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData extends LoginCredentials {
  full_name: string
}

export interface GoogleAuthResponse {
  access_token: string
  token_type: string
  user: User
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

export interface QRCode {
  id: string
  user_id: string
  type: string
  content: string
  tracking_id: string
  created_at: string
  updated_at: string
  qr_image: string
  qr_image_url: string
  metadata?: Record<string, any>
} 