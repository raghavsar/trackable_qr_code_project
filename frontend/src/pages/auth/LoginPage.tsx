"use client"

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { toast } from "react-hot-toast"
import { useAuth } from "@/hooks/useAuth"
import { Loader2 } from "lucide-react"
import { authService } from "@/services/auth"
import { GoogleLogin } from '@react-oauth/google'

export default function LoginPage() {
  const navigate = useNavigate()
  const { setUser, setToken } = useAuth()
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({
    email: "",
    password: ""
  })

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!formData.email || !formData.password) {
      toast.error("Please enter both email and password")
      return
    }
    
    try {
      setLoading(true)
      console.log("Attempting login with:", formData.email)
      const response = await authService.login(formData)
      console.log("Login successful")
      // Update auth context with user and token
      setUser(response.user)
      setToken(response.access_token)
      toast.success("Login successful!")
      navigate("/")
    } catch (error) {
      console.error("Login failed:", error)
      toast.error("Invalid email or password")
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleSuccess = async (credentialResponse: any) => {
    try {
      setLoading(true)
      console.log('Google login response:', credentialResponse);
      
      if (!credentialResponse.credential) {
        console.error('No credential received from Google');
        toast.error('Failed to receive login credentials from Google');
        return;
      }
      
      const response = await authService.handleGoogleLogin(
        credentialResponse.credential,
        window.location.origin + '/auth/google/callback'
      );
      
      console.log('Backend response:', response);
      
      if (response.user && response.access_token) {
        setUser(response.user);
        setToken(response.access_token);
        toast.success("Successfully logged in with Google!");
        navigate("/");
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (error: any) {
      console.error("Google login failed:", error);
      const errorMessage = error.response?.data?.detail || error.message || "Failed to login with Google";
      toast.error(errorMessage);
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleError = () => {
    console.error("Google login failed");
    toast.error("Failed to login with Google");
    setLoading(false);
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl text-center font-bold">Login</CardTitle>
          <CardDescription className="text-center">
            Enter your email and password to login
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                required
                disabled={loading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={formData.password}
                onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                required
                disabled={loading}
              />
            </div>
            <Button
              type="submit"
              className="w-full"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Logging in...
                </>
              ) : (
                "Login with Email"
              )}
            </Button>
          </form>

          <div className="mt-4">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white px-2 text-gray-500">
                  Or continue with
                </span>
              </div>
            </div>

            <div className="mt-4 flex justify-center">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={handleGoogleError}
                useOneTap={false}
                theme="outline"
                size="large"
                text="continue_with"
                shape="rectangular"
                width="300"
                type="standard"
                context="signin"
              />
            </div>
          </div>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Don't have an account?{" "}
              <Button
                variant="link"
                className="p-0 h-auto font-semibold"
                onClick={() => navigate("/auth/register")}
              >
                Create an account
              </Button>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
} 