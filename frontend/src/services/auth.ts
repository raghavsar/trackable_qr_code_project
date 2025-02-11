import type { User } from '@/types'
import { axiosInstance } from "./axios"
import { AxiosInstance } from "axios"

// Consolidate the response interfaces
export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface LoginData {
  email: string
  password: string
}

class AuthService {
  private api: AxiosInstance;

  constructor() {
    this.api = axiosInstance;
  }

  private handleError(error: any): never {
    console.error('API Error:', {
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    });
    throw error;
  }

  async login(data: LoginData): Promise<AuthResponse> {
    const response = await this.api.post<AuthResponse>("/auth/login", data)
    return response.data
  }

  async handleGoogleLogin(credential: string, redirectUri: string): Promise<AuthResponse> {
    try {
      const response = await this.api.post<AuthResponse>('/auth/google/callback', {
        credential,
        redirect_uri: redirectUri
      });
      
      // Ensure the auth_provider is correctly typed
      const data = response.data;
      if (data.user.auth_provider !== "email" && data.user.auth_provider !== "google") {
        throw new Error("Invalid auth_provider received from server");
      }
      
      return data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async register(data: LoginData): Promise<AuthResponse> {
    const response = await this.api.post<AuthResponse>("/auth/register", data)
    return response.data
  }

  async getProfile(): Promise<User> {
    const response = await this.api.get<User>("/auth/me")
    return response.data
  }

  async logout(): Promise<void> {
    // Clear the token from axios instance
    if (this.api.defaults.headers.common['Authorization']) {
      delete this.api.defaults.headers.common['Authorization'];
    }
    // Clear token from localStorage
    localStorage.removeItem('token');
  }
}

export const authService = new AuthService()