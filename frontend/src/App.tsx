import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Layout } from "./components/Layout"
import { Toaster } from "react-hot-toast"
import AuthProvider from "./providers/AuthProvider"
import LoginPage from "./pages/auth/LoginPage"
import RegisterPage from "./pages/auth/RegisterPage"
import ProfilePage from "./pages/profile/ProfilePage"
import AccountSettings from "./pages/settings/AccountSettings"
import "./styles/globals.css"
import GoogleCallback from "./pages/auth/GoogleCallback"
import { ProtectedRoute } from "./components/ProtectedRoute"
import AnalyticsDashboard from "./pages/analytics/Dashboard"
import VCardAnalytics from "./pages/analytics/QRCodeAnalytics"
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { GoogleOAuthProvider } from '@react-oauth/google'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import VCardForm from "@/components/QRGenerator/VCardForm"
import VCardRedirect from "@/pages/VCardRedirect"
import { LandingPage } from "@/components/LandingPage"
import { useAuth } from "@/hooks/useAuth"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { QrCode, FileText, Link } from "lucide-react"

const queryClient = new QueryClient()

const Dashboard = () => {
  return (
    <Card className="border shadow-sm overflow-hidden mb-8">
      <CardHeader className="pb-4 bg-gray-50/80 border-b">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center">
          <div>
            <CardTitle className="text-xl font-bold">QR Code Generator</CardTitle>
            <CardDescription className="text-muted-foreground mt-1">
              Create and manage your QR codes and digital assets
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <Tabs defaultValue="qr-codes" className="w-full">
          <div className="px-6 pt-6 pb-2 border-b">
            <TabsList className="w-full sm:w-auto grid grid-cols-3 sm:inline-flex">
              <TabsTrigger value="qr-codes" className="gap-2">
                <QrCode className="h-4 w-4" />
                <span>QR Codes</span>
              </TabsTrigger>
              <TabsTrigger value="pages" className="gap-2">
                <FileText className="h-4 w-4" />
                <span>Pages</span>
              </TabsTrigger>
              <TabsTrigger value="short-links" className="gap-2">
                <Link className="h-4 w-4" />
                <span>Short Links</span>
              </TabsTrigger>
            </TabsList>
          </div>

          <div className="p-6">
            <TabsContent value="qr-codes" className="mt-0 space-y-8">
              <VCardForm />
            </TabsContent>

            <TabsContent value="pages" className="mt-0">
              <div className="flex flex-col items-center justify-center py-12 text-center border rounded-lg border-dashed bg-muted/20">
                <FileText className="h-16 w-16 text-muted-foreground mb-4 opacity-50" />
                <h3 className="text-lg font-medium mb-2">Landing Pages Coming Soon</h3>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  This feature is currently under development. You'll soon be able to create custom landing pages for your QR codes.
                </p>
              </div>
            </TabsContent>

            <TabsContent value="short-links" className="mt-0">
              <div className="flex flex-col items-center justify-center py-12 text-center border rounded-lg border-dashed bg-muted/20">
                <Link className="h-16 w-16 text-muted-foreground mb-4 opacity-50" />
                <h3 className="text-lg font-medium mb-2">URL Shortener Coming Soon</h3>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  This feature is currently under development. You'll soon be able to create and track shortened URLs.
                </p>
              </div>
            </TabsContent>
          </div>
        </Tabs>
      </CardContent>
    </Card>
  )
}

const HomeRoute = () => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <Dashboard /> : <LandingPage />;
}

function App() {
  console.log('App component is rendering')
  
  try {
    return (
      <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <AuthProvider>
              <Toaster position="top-right" />
              <Routes>
                <Route path="/r/:id" element={<VCardRedirect />} />
                <Route path="/" element={<Layout />}>
                  <Route index element={<HomeRoute />} />
                  <Route path="dashboard" element={
                    <ProtectedRoute>
                      <Dashboard />
                    </ProtectedRoute>
                  } />
                  <Route path="auth/login" element={<LoginPage />} />
                  <Route path="auth/register" element={<RegisterPage />} />
                  <Route path="profile" element={
                    <ProtectedRoute>
                      <ProfilePage />
                    </ProtectedRoute>
                  } />
                  <Route path="settings" element={
                    <ProtectedRoute>
                      <AccountSettings />
                    </ProtectedRoute>
                  } />
                  <Route path="auth/google/callback" element={<GoogleCallback />} />
                  <Route path="analytics" element={
                    <ProtectedRoute>
                      <AnalyticsDashboard />
                    </ProtectedRoute>
                  } />
                  <Route path="analytics/vcard/:id" element={
                    <ProtectedRoute>
                      <VCardAnalytics />
                    </ProtectedRoute>
                  } />
                  <Route path="analytics/qr/:id" element={
                    <ProtectedRoute>
                      <VCardAnalytics />
                    </ProtectedRoute>
                  } />
                </Route>
              </Routes>
            </AuthProvider>
          </BrowserRouter>
          <ReactQueryDevtools initialIsOpen={false} />
        </QueryClientProvider>
      </GoogleOAuthProvider>
    )
  } catch (error) {
    console.error('Error in App component:', error)
    return <div>Error loading application. Check console for details.</div>
  }
}

export default App 