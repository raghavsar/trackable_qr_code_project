import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card } from "@/components/ui/card"
import { FileText, Link2, Contact2, BarChart3, User, LogOut, Settings } from 'lucide-react'
import VCardForm from "@/components/QRGenerator/VCardForm"
import LandingPageForm from "@/components/QRGenerator/LandingPageForm"
import ShortLinkForm from "@/components/QRGenerator/ShortLinkForm"
import GeneratedQRList from "@/components/QRGenerator/GeneratedQRList"
import { Button } from "./ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"
import { useNavigate, useLocation, Outlet } from "react-router-dom"
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
  console.log('Layout component rendering')
  
  const navigate = useNavigate()
  const location = useLocation()
  const { user, isAuthenticated, isLoading, logout } = useAuth()

  console.log('Auth state:', { isAuthenticated, isLoading, user })

  // Show loading state while checking authentication
  if (isLoading) {
    console.log('Showing loading spinner')
    return <LoadingSpinner />
  }

  // If not authenticated, show login prompt
  if (!isAuthenticated) {
    console.log('Not authenticated, showing login prompt')
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="border-b bg-white">
          <div className="container max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-semibold">QR Code Generator</h1>
            </div>
            <Button onClick={() => navigate('/auth/login')}>
              Login
            </Button>
          </div>
        </header>

        <div className="container max-w-5xl mx-auto p-4">
          <div className="text-center py-12">
            <h2 className="text-2xl font-bold mb-4">Welcome to QR Code Generator</h2>
            <p className="text-gray-600 mb-8">Please login to create and manage your QR codes.</p>
            <Button size="lg" onClick={() => navigate('/auth/login')}>
              Login to Get Started
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // Show loading state if authenticated but user data not loaded yet
  if (!user) {
    console.log('User data not loaded, showing loading spinner')
    return <LoadingSpinner />
  }

  console.log('Rendering main layout')
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b bg-white">
        <div className="container max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-semibold">QR Code Generator</h1>
          </div>
          
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-8 w-8 p-0">
                <span className="sr-only">Open menu</span>
                <User className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <div className="flex items-center justify-start gap-2 p-2">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">{user.full_name}</p>
                  <p className="text-xs leading-none text-muted-foreground">
                    {user.email}
                  </p>
                </div>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate('/profile')}>
                <User className="mr-2 h-4 w-4" />
                Profile
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate('/settings')}>
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuItem onClick={logout}>
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      <main className="container max-w-7xl mx-auto p-4">
        <ErrorBoundary>
          {location.pathname === '/' ? (
            <Tabs defaultValue="vcard" className="space-y-4">
              <TabsList>
                <TabsTrigger value="vcard">
                  <Contact2 className="h-4 w-4 mr-2" />
                  VCard
                </TabsTrigger>
                <TabsTrigger value="landing-page">
                  <FileText className="h-4 w-4 mr-2" />
                  Landing Page
                </TabsTrigger>
                <TabsTrigger value="short-link">
                  <Link2 className="h-4 w-4 mr-2" />
                  Short Link
                </TabsTrigger>
                <TabsTrigger value="analytics" onClick={() => navigate('/analytics')}>
                  <BarChart3 className="h-4 w-4 mr-2" />
                  Analytics
                </TabsTrigger>
              </TabsList>
              
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
                <Card className="p-4 col-span-full">
                  <TabsContent value="vcard" className="m-0">
                    <ErrorBoundary>
                      <VCardForm />
                    </ErrorBoundary>
                  </TabsContent>
                  <TabsContent value="landing-page" className="m-0">
                    <ErrorBoundary>
                      <LandingPageForm />
                    </ErrorBoundary>
                  </TabsContent>
                  <TabsContent value="short-link" className="m-0">
                    <ErrorBoundary>
                      <ShortLinkForm />
                    </ErrorBoundary>
                  </TabsContent>
                </Card>
                
                {/* Temporarily disabled to reduce error logs */}
                {/* <div className="col-span-full lg:col-span-3">
                  <ErrorBoundary>
                    <GeneratedQRList />
                  </ErrorBoundary>
                </div> */}
              </div>
            </Tabs>
          ) : (
            <Outlet />
          )}
        </ErrorBoundary>
      </main>
    </div>
  )
} 