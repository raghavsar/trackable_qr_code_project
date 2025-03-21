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

const queryClient = new QueryClient()

const Dashboard = () => {
  return (
    <Tabs defaultValue="qr-codes" className="space-y-6">
      <TabsList>
        <TabsTrigger value="qr-codes">QR Codes</TabsTrigger>
        <TabsTrigger value="pages">Pages</TabsTrigger>
        <TabsTrigger value="short-links">Short Links</TabsTrigger>
      </TabsList>

      <TabsContent value="qr-codes" className="space-y-8">
        <div className="grid gap-6">
          <div className="space-y-4">
            <h2 className="text-2xl font-bold">Create New QR Code</h2>
            <VCardForm />
          </div>

          <div className="space-y-4">
            <h2 className="text-2xl font-bold">Your QR Codes</h2>
          </div>
        </div>
      </TabsContent>

      <TabsContent value="pages">
        <p>Landing pages coming soon...</p>
      </TabsContent>

      <TabsContent value="short-links">
        <p>URL shortener coming soon...</p>
      </TabsContent>
    </Tabs>
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