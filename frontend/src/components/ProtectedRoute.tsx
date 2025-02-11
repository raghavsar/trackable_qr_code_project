import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  console.log('ProtectedRoute - Checking auth...');
  const { isAuthenticated, isLoading } = useAuth();

  console.log('ProtectedRoute state:', { isAuthenticated, isLoading });

  if (isLoading) {
    console.log('ProtectedRoute - Loading...');
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    console.log('ProtectedRoute - Not authenticated, redirecting...');
    return <Navigate to="/auth/login" />;
  }

  console.log('ProtectedRoute - Authenticated, rendering children');
  return <>{children}</>;
} 