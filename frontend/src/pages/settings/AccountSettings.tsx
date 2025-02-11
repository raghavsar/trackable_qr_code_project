import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/hooks/useAuth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Loader2, User, Lock, Bell } from "lucide-react"
import { toast } from "react-hot-toast"
import { authService } from "@/services/auth"

export default function AccountSettings() {
  const navigate = useNavigate()
  const { user, loading } = useAuth()
  const [isUpdating, setIsUpdating] = useState(false)
  const [profileData, setProfileData] = useState({
    full_name: user?.full_name || "",
    email: user?.email || "",
  })

  const [securityData, setSecurityData] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  })

  if (!user) {
    navigate("/auth/login")
    return null
  }

  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setIsUpdating(true)
      const updatedUser = await authService.updateProfile({
        full_name: profileData.full_name,
        email: profileData.email,
      })
      setProfileData({
        full_name: updatedUser.full_name,
        email: updatedUser.email,
      })
      toast.success("Profile updated successfully")
    } catch (error) {
      console.error("Failed to update profile:", error)
      toast.error("Failed to update profile")
    } finally {
      setIsUpdating(false)
    }
  }

  const handlePasswordUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (securityData.new_password !== securityData.confirm_password) {
      toast.error("New passwords don't match")
      return
    }
    try {
      setIsUpdating(true)
      await authService.updatePassword({
        current_password: securityData.current_password,
        new_password: securityData.new_password,
      })
      toast.success("Password updated successfully")
      setSecurityData({
        current_password: "",
        new_password: "",
        confirm_password: "",
      })
    } catch (error) {
      console.error("Failed to update password:", error)
      toast.error("Failed to update password")
    } finally {
      setIsUpdating(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="container max-w-4xl mx-auto py-8 px-4 space-y-8">
      <h1 className="text-3xl font-bold">Account Settings</h1>

      {/* Profile Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Profile Information
          </CardTitle>
          <CardDescription>
            Update your profile information and email address
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 mb-6">
            {user.auth_provider === "google" && user.profile_picture ? (
              <img
                src={user.profile_picture}
                alt={user.full_name}
                className="h-16 w-16 rounded-full object-cover"
              />
            ) : (
              <div className="h-16 w-16 rounded-full bg-gray-200 flex items-center justify-center">
                <User className="h-8 w-8 text-gray-500" />
              </div>
            )}
            {user.auth_provider === "google" && (
              <p className="text-sm text-muted-foreground">
                Profile picture is managed by your Google account
              </p>
            )}
          </div>
          <form onSubmit={handleProfileUpdate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="full_name">Full Name</Label>
              <Input
                id="full_name"
                value={profileData.full_name}
                onChange={(e) =>
                  setProfileData((prev) => ({
                    ...prev,
                    full_name: e.target.value,
                  }))
                }
                disabled={isUpdating}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={profileData.email}
                onChange={(e) =>
                  setProfileData((prev) => ({ ...prev, email: e.target.value }))
                }
                disabled={isUpdating || user.auth_provider === "google"}
              />
              {user.auth_provider === "google" && (
                <p className="text-sm text-muted-foreground">
                  Email cannot be changed for Google accounts
                </p>
              )}
            </div>
            <Button type="submit" disabled={isUpdating}>
              {isUpdating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Updating...
                </>
              ) : (
                "Update Profile"
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Security Section */}
      {user.auth_provider === "email" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lock className="h-5 w-5" />
              Security
            </CardTitle>
            <CardDescription>
              Update your password and security settings
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handlePasswordUpdate} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="current_password">Current Password</Label>
                <Input
                  id="current_password"
                  type="password"
                  value={securityData.current_password}
                  onChange={(e) =>
                    setSecurityData((prev) => ({
                      ...prev,
                      current_password: e.target.value,
                    }))
                  }
                  disabled={isUpdating}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="new_password">New Password</Label>
                <Input
                  id="new_password"
                  type="password"
                  value={securityData.new_password}
                  onChange={(e) =>
                    setSecurityData((prev) => ({
                      ...prev,
                      new_password: e.target.value,
                    }))
                  }
                  disabled={isUpdating}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm_password">Confirm New Password</Label>
                <Input
                  id="confirm_password"
                  type="password"
                  value={securityData.confirm_password}
                  onChange={(e) =>
                    setSecurityData((prev) => ({
                      ...prev,
                      confirm_password: e.target.value,
                    }))
                  }
                  disabled={isUpdating}
                />
              </div>
              <Button type="submit" disabled={isUpdating}>
                {isUpdating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Updating...
                  </>
                ) : (
                  "Update Password"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Preferences Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Preferences
          </CardTitle>
          <CardDescription>
            Manage your notification and display preferences
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Notification preferences coming soon
          </p>
        </CardContent>
      </Card>
    </div>
  )
} 