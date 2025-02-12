import { BrowserRouter, Routes, Route, useParams } from "react-router-dom"
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
import QRCodeAnalytics from "./pages/analytics/QRCodeAnalytics"
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { GoogleOAuthProvider } from '@react-oauth/google'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import VCardForm from "@/components/QRGenerator/VCardForm"
import QRCodeList from "@/components/QRGenerator/QRCodeList"
import { useEffect } from "react"
import { useNavigate } from "react-router-dom"

// VCard Redirect Component
function VCardRedirect() {
  const { id } = useParams()
  const navigate = useNavigate()
  
  useEffect(() => {
    if (!id) {
      navigate('/')
      return
    }

    // Direct redirect without forcing VCF format
    window.location.href = `http://192.168.7.154:8005/r/${id}`
  }, [id, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
        <p className="text-lg">Preparing your contact...</p>
      </div>
    </div>
  )
}

const queryClient = new QueryClient()

console.log('App.tsx is executing')

function App() {
  console.log('App component is rendering')
  
  try {
    return (
      <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <AuthProvider>
              <Routes>
                <Route path="/r/:id" element={<VCardRedirect />} />
                <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                  <Route index element={
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
                            <QRCodeList />
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
                  } />
                  <Route path="/profile" element={
                    <ProtectedRoute>
                      <ProfilePage />
                    </ProtectedRoute>
                  } />
                  <Route path="/settings" element={
                    <ProtectedRoute>
                      <AccountSettings />
                    </ProtectedRoute>
                  } />
                  <Route path="/analytics" element={
                    <ProtectedRoute>
                      <AnalyticsDashboard />
                    </ProtectedRoute>
                  } />
                  <Route path="/analytics/qr/:id" element={
                    <ProtectedRoute>
                      <QRCodeAnalytics />
                    </ProtectedRoute>
                  } />
                </Route>
                <Route path="/auth/login" element={<LoginPage />} />
                <Route path="/auth/register" element={<RegisterPage />} />
                <Route path="/auth/google/callback" element={<GoogleCallback />} />
              </Routes>
              <Toaster position="bottom-right" />
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