import { User, LogOut, Settings } from 'lucide-react'
import { Button } from "./ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"
import { useNavigate, Outlet, useLocation } from "react-router-dom"
import { useAuth } from "@/hooks/useAuth"
import { ErrorBoundary } from "./ErrorBoundary"
import { LandingPage } from "./LandingPage"

// Loading spinner component
const LoadingSpinner = () => (
  <div className="min-h-screen bg-gray-50 flex items-center justify-center">
    <div className="text-center">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
      <p className="mt-4 text-gray-600">Loading...</p>
    </div>
  </div>
)

export function Layout() {
  const navigate = useNavigate()
  const { isAuthenticated, isLoading, user, logout } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <LoadingSpinner />
  }

  // Special routes that don't need the full layout
  const isSpecialRoute = ['/auth/login', '/auth/register', '/auth/google/callback'].includes(location.pathname)
  if (isSpecialRoute) {
    return <Outlet />
  }

  // For authenticated users, show the app layout
  if (isAuthenticated && user) {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white border-b">
          <div className="container max-w-7xl mx-auto h-16 px-4 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button 
                variant="ghost" 
                className="font-semibold"
                onClick={() => navigate('/')}
              >
                QR Code Generator
              </Button>
            </div>
            
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="h-8 w-8 p-0">
                  <span className="sr-only">Open menu</span>
                  <User className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => navigate('/profile')}>
                  <User className="mr-2 h-4 w-4" />
                  Profile
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate('/settings')}>
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => {
                  logout()
                  navigate('/')
                }}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>
        
        <main className="container max-w-7xl mx-auto py-6">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    )
  }

  // For unauthenticated users, just render the content (which should be the landing page)
  return <Outlet />
} 