import { ReactNode, createContext, useEffect, useState } from 'react';
import { authService } from '@/services/auth';
import { User } from '@/types';
import { AuthContextType } from '@/types/auth';

interface Props {
  children: ReactNode;
}

const defaultContext: AuthContextType = {
  isAuthenticated: false,
  user: null,
  token: null,
  loading: true,
  isLoading: true,
  setUser: () => {},
  setToken: () => {},
  logout: () => {}
};

export const AuthContext = createContext<AuthContextType>(defaultContext);

export default function AuthProvider({ children }: Props) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const isAuthenticated = Boolean(token);

  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = localStorage.getItem('token');
      if (storedToken) {
        try {
          const userData = await authService.getProfile();
          setUser(userData);
        } catch (error) {
          console.error('Failed to initialize auth:', error);
          // Clear invalid token
          localStorage.removeItem('token');
          setToken(null);
        }
      }
      setLoading(false);
    };

    initializeAuth();
  }, []);

  const handleSetToken = (newToken: string) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
  };

  const handleLogout = () => {
    authService.logout();
    setToken(null);
    setUser(null);
  };

  const contextValue: AuthContextType = {
    isAuthenticated,
    user,
    token,
    loading,
    isLoading: loading,
    setUser,
    setToken: handleSetToken,
    logout: handleLogout
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
} 