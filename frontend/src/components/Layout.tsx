import { User, LogOut, Settings, BarChart2, QrCode } from 'lucide-react'
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
        <header className="bg-white border-b shadow-sm sticky top-0 z-50">
          <div className="container max-w-7xl mx-auto h-16 px-4 flex items-center justify-between">
            <div className="flex items-center space-x-1">
              <Button 
                variant="ghost" 
                className="font-semibold flex items-center gap-2 text-primary"
                onClick={() => navigate('/')}
              >
                <QrCode className="h-5 w-5" />
                <span>QR Code Generator</span>
              </Button>
            </div>
            
            <div className="flex items-center space-x-2">
              <Button
                variant="ghost"
                size="sm"
                className="flex items-center gap-1.5 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                onClick={() => navigate('/analytics')}
              >
                <BarChart2 className="h-4 w-4" />
                <span>Analytics</span>
              </Button>
              
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full">
                    <span className="sr-only">Open menu</span>
                    <User className="h-5 w-5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <div className="flex items-center justify-start p-2">
                    <div className="flex flex-col">
                      <p className="font-medium">{user.email}</p>
                    </div>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => navigate('/profile')} className="cursor-pointer">
                    <User className="mr-2 h-4 w-4" />
                    Profile
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => navigate('/settings')} className="cursor-pointer">
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem 
                    onClick={() => {
                      logout()
                      navigate('/')
                    }}
                    className="cursor-pointer text-red-600 focus:text-red-700 focus:bg-red-50"
                  >
                    <LogOut className="mr-2 h-4 w-4" />
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </header>
        
        <main className="container max-w-7xl mx-auto py-6 px-4">
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