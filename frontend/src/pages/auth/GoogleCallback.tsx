import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { authService } from '@/services/auth';
import { User } from '@/types';

interface GoogleCallbackResponse {
  access_token: string;
  user: User;
}

const GoogleCallback = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setUser, setToken } = useAuth();

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state') || undefined;
    
    if (code) {
      // Exchange code for token
      authService.handleGoogleCallback(code, state)
        .then((response: GoogleCallbackResponse) => {
          // Set both token and user in auth context
          setToken(response.access_token);
          setUser(response.user);
          
          // Redirect to home page
          navigate('/', { replace: true });
        })
        .catch((error) => {
          console.error('Google login error:', error);
          navigate('/auth/login', { 
            state: { 
              error: 'Failed to complete Google login' 
            },
            replace: true
          });
        });
    } else {
      // Handle error case
      console.error('No authorization code received');
      navigate('/auth/login', { 
        state: { 
          error: 'Failed to complete Google login' 
        },
        replace: true
      });
    }
  }, [searchParams, navigate, setUser, setToken]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h2 className="text-2xl font-semibold mb-4">
          Completing Google Login...
        </h2>
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
      </div>
    </div>
  );
};

export default GoogleCallback; 