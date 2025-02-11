export interface UserResponse {
  _id: string;
  email: string;
  full_name: string;
  profile_picture?: string | null;
  auth_provider: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  is_superuser: boolean;
  password_hash?: string | null;
}

// Make User identical to UserResponse since we're getting the data directly from the backend
export type User = UserResponse; 