"use client"

import * as React from 'react'
import { useState } from "react"
import { Button } from "../ui/button"
import { Input } from "../ui/input"
import { Label } from "../ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../ui/card"
import { Textarea } from "../ui/textarea"
import { toast } from 'react-hot-toast'
import { qrService } from '@/services/api'
import type { QRCodeResponse } from '@/types/api'
import {
  ChevronRight,
  User, Briefcase, MapPin, Mail, Phone, Globe, FileText,
  Upload, PlusCircle, QrCode, Check,
  CreditCard, ToggleLeft, ToggleRight
}
from 'lucide-react'
import { Switch } from "../ui/switch"
import QRCodeEditor from './QRCodeEditor'
import QRCodeList from './QRCodeList'
import { Badge } from "../ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs"
import { PhoneNumberInput } from '../PhoneNumberInput'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from "../ui/alert-dialog"

interface FormData {
  first_name: string
  last_name: string
  email: string
  mobile_number: string
  work_number: string | undefined
  profile_picture: string | undefined
  company: string | undefined
  title: string | undefined
  website: string | undefined
  address: {
    street: string | undefined
    city: string | undefined
    state: string | undefined
    country: string | undefined
    zip_code: string | undefined
  } | undefined
  notes: string | undefined
}

const ProfilePictureUpload = ({
  profilePicture,
  onFileChange
}: {
  profilePicture: string | undefined;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) => {
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = React.useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      // Create a synthetic event to reuse the existing handler
      const event = {
        target: {
          files: e.dataTransfer.files
        }
      } as unknown as React.ChangeEvent<HTMLInputElement>;

      onFileChange(event);
    }
  };

  return (
    <div
      className={`w-full flex flex-col items-center space-y-4 p-6 rounded-lg border-2 border-dashed transition-colors ${
        isDragging ? 'border-primary bg-primary/5' : 'border-gray-200 hover:border-gray-300'
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div
        className="relative group cursor-pointer"
        onClick={() => fileInputRef.current?.click()}
      >
        <div className="w-28 h-28 rounded-full overflow-hidden border-2 border-white shadow-md transition-transform group-hover:scale-105">
          {profilePicture ? (
            <img
              src={profilePicture}
              alt="Profile"
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200">
              <User className="h-12 w-12 text-gray-400" />
            </div>
          )}
        </div>

        <div className="absolute inset-0 flex items-center justify-center rounded-full bg-black/30 text-white opacity-0 group-hover:opacity-100 transition-opacity">
          <Upload className="h-6 w-6" />
        </div>

        {profilePicture && (
          <div className="absolute -bottom-1 -right-1">
            <Badge className="bg-primary text-white border-2 border-white shadow-sm">
              <Check className="h-3 w-3 mr-1" />
              <span className="text-xs font-medium">Uploaded</span>
            </Badge>
          </div>
        )}
      </div>

      <div className="text-center">
        <input
          type="file"
          accept="image/*"
          onChange={onFileChange}
          className="hidden"
          ref={fileInputRef}
        />

        <Button
          type="button"
          variant="outline"
          className="mb-2"
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="mr-2 h-4 w-4" />
          {profilePicture ? 'Change Photo' : 'Upload Image'}
        </Button>

        <p className="text-xs text-muted-foreground">
          JPG, PNG or GIF • Max 5MB
        </p>

        <div className="mt-2 text-xs text-muted-foreground">
          Or drop image here
        </div>
      </div>
    </div>
  );
};

export default function VCardForm() {
  const [formData, setFormData] = useState<FormData>({
    first_name: "",
    last_name: "",
    email: "",
    mobile_number: "",
    work_number: undefined,
    profile_picture: undefined,
    company: undefined,
    title: undefined,
    website: undefined,
    address: {
      street: undefined,
      city: undefined,
      state: undefined,
      country: undefined,
      zip_code: undefined
    },
    notes: undefined
  })

  const [loading, setLoading] = useState(false)
  const [qrCode, setQrCode] = useState<QRCodeResponse | null>(null)
  const [showEditor, setShowEditor] = useState(false)
  const [activeTab, setActiveTab] = useState("personal")
  const qrListRef = React.useRef<{ refreshList: () => void } | null>(null)
  const [deleteCodeId, setDeleteCodeId] = useState<string | null>(null)
  const [useDefaultAddress, setUseDefaultAddress] = useState(true)

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    if (name.startsWith('address.')) {
      const addressField = name.split('.')[1] as keyof typeof formData.address
      setFormData(prev => ({
        ...prev,
        address: {
          ...prev.address!,
          [addressField]: value || undefined
        }
      }))
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value || undefined
      }))
    }
  }

  // Add handler for phone number changes
  const handlePhoneChange = (field: 'mobile_number' | 'work_number') => (value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value || undefined
    }));
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        toast.error("Profile picture must be less than 5MB");
        return;
      }

      const reader = new FileReader();
      reader.onloadend = () => {
        setFormData(prev => ({
          ...prev,
          profile_picture: reader.result as string
        }));
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setLoading(true)

      // If using default address, clear any custom address values
      let submissionData = {...formData}
      if (useDefaultAddress) {
        submissionData.address = {
          street: undefined,  // The backend will use the default address
          city: undefined,
          state: undefined,
          country: undefined,
          zip_code: undefined
        }
      }

      // Create VCard first
      const vcard = await qrService.createVCard(submissionData)
      // Generate QR code with direct vCard data
      const qrCode = await qrService.generateQRCode({
        vcard_id: vcard._id || vcard.id,
        design: {
          box_size: 10,
          border: 4,
          foreground_color: '#000000',
          background_color: '#FFFFFF',
          eye_color: '#000000',
          module_color: '#000000',
          pattern_style: 'square',
          error_correction: 'H',
          logo_url: undefined,
          logo_size: undefined,
          logo_background: false,
          logo_round: false
        }
      })
      setQrCode(qrCode)
      // Refresh QR code list after successful generation
      qrListRef.current?.refreshList()
      toast.success('QR code generated successfully')
    } catch (error) {
      console.error('Failed to generate QR code:', error)
      toast.error('Failed to generate QR code')
    } finally {
      setLoading(false)
    }
  }

  const handleShare = async (qrCode: QRCodeResponse | any) => {
    try {
      // Log the QR code object to help with debugging
      console.log('Share attempt with QR code data:', qrCode);

      // Get vcard_id from either root level or metadata
      const vcardId = qrCode.vcard_id || (qrCode.metadata && qrCode.metadata.vcard_id);

      console.log('Extracted vCard ID:', vcardId);

      if (!vcardId) {
        console.error('Missing vCard ID in QR code data');
        toast.error('Cannot share: Missing VCard ID');
        return;
      }

      // Determine name to use in share message
      const name = qrCode.metadata?.vcard_name ||
                   `${qrCode.metadata?.firstName || ''} ${qrCode.metadata?.lastName || ''}`.trim() ||
                   'Digital Business Card';

      const redirectUrl = `${window.location.origin}/r/${vcardId}`;
      console.log('Share URL:', redirectUrl);

      // Check if Web Share API is available and supported
      if (navigator.share && typeof navigator.share === 'function') {
        console.log('Using Web Share API');
        try {
          await navigator.share({
            title: `${name}'s Digital Business Card`,
            text: `Check out ${name}'s digital business card!`,
            url: redirectUrl
          });
          toast.success('Shared successfully!');
        } catch (shareError) {
          console.error('Web Share API error:', shareError);

          // If share was aborted by user, don't show error
          if (shareError instanceof Error && shareError.name === 'AbortError') {
            console.log('Share canceled by user');
            return;
          }

          // Fallback to clipboard if Web Share API fails
          await fallbackToClipboard(redirectUrl);
        }
      } else {
        console.log('Web Share API not supported, using clipboard fallback');
        await fallbackToClipboard(redirectUrl);
      }
    } catch (error) {
      console.error('Error in handleShare:', error);
      toast.error('Failed to share QR code');
    }
  };

  // Helper function for clipboard fallback
  const fallbackToClipboard = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      toast.success('Link copied to clipboard!');
    } catch (clipboardError) {
      console.error('Clipboard write error:', clipboardError);

      // Use the execCommand fallback for older browsers
      try {
        const textArea = document.createElement('textarea');
        textArea.value = url;
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        const successful = document.execCommand('copy');
        document.body.removeChild(textArea);

        if (successful) {
          toast.success('Link copied to clipboard!');
        } else {
          throw new Error('execCommand copy failed');
        }
      } catch (legacyError) {
        console.error('Legacy clipboard fallback error:', legacyError);
        toast.error('Could not copy to clipboard. Please copy the URL manually.');
      }
    }
  };

  const confirmDelete = async () => {
    if (!deleteCodeId) return;

    try {
      await qrService.deleteQRCode(deleteCodeId)
      toast.success('QR code deleted successfully')
      qrListRef.current?.refreshList()
      setDeleteCodeId(null)
    } catch (error) {
      console.error('Failed to delete QR code:', error)
      toast.error('Failed to delete QR code')
    }
  }

  const handleEdit = (code: QRCodeResponse) => {
    setQrCode(code)
    setShowEditor(true)
  }

  const handleUpdateComplete = () => {
    setShowEditor(false)
  }

  const isFormComplete = () => {
    return formData.first_name &&
           formData.last_name &&
           formData.email &&
           formData.mobile_number;
  };

  return (
    <div className="container mx-auto p-4 space-y-10 max-w-7xl">
      <AlertDialog open={!!deleteCodeId} onOpenChange={(isOpen: boolean) => !isOpen && setDeleteCodeId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the QR code.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {showEditor && qrCode ? (
        <QRCodeEditor
          qrCode={qrCode}
          onUpdate={handleUpdateComplete}
          onBack={() => setShowEditor(false)}
        />
      ) : (
        <>
          <Card className="border shadow-sm overflow-hidden">
            <CardHeader className="pb-4 bg-gray-50/80 border-b">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center">
                <div>
                  <CardTitle className="text-2xl font-bold text-primary">Create New QR Code</CardTitle>
                  <CardDescription className="text-muted-foreground mt-1">
                    Fill out the form to generate a digital business card QR code
                  </CardDescription>
                </div>
                <Badge variant="outline" className="mt-2 sm:mt-0 flex items-center gap-1.5 bg-white">
                  <CreditCard className="h-3.5 w-3.5" />
                  New VCard
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="p-0">
              <form onSubmit={handleSubmit} className="space-y-6">
                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                  <div className="px-6 pt-6 pb-2 border-b">
                    <TabsList className="mb-0 w-full sm:w-auto grid grid-cols-3 sm:inline-flex">
                      <TabsTrigger value="personal" className="gap-2">
                        <User className="h-4 w-4" />
                        <span className="hidden sm:inline">Personal Details</span>
                        <span className="sm:hidden">Personal</span>
                      </TabsTrigger>
                      <TabsTrigger value="company" className="gap-2">
                        <Briefcase className="h-4 w-4" />
                        <span className="hidden sm:inline">Company Details</span>
                        <span className="sm:hidden">Company</span>
                      </TabsTrigger>
                      <TabsTrigger value="contact" className="gap-2">
                        <MapPin className="h-4 w-4" />
                        <span className="hidden sm:inline">Address & Contact</span>
                        <span className="sm:hidden">Contact</span>
                      </TabsTrigger>
                    </TabsList>
                  </div>

                  <div className="p-6">
                    <TabsContent value="personal" className="mt-0">
                      <div className="space-y-4">
                        <div className="space-y-4 mb-6">
                          <h3 className="text-base font-medium leading-6 text-gray-900">Profile Picture</h3>
                          <ProfilePictureUpload
                            profilePicture={formData.profile_picture}
                            onFileChange={handleFileChange}
                          />
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div className="space-y-1.5">
                            <Label htmlFor="first_name" className="text-sm font-medium">
                              <User className="h-3.5 w-3.5 inline mr-1.5" />
                              First name <span className="text-red-500">*</span>
                            </Label>
                            <Input
                              id="first_name"
                              name="first_name"
                              value={formData.first_name}
                              onChange={handleInputChange}
                              required
                              placeholder="Enter your first name"
                              className="border-muted-foreground/20"
                            />
                          </div>
                          <div className="space-y-1.5">
                            <Label htmlFor="last_name" className="text-sm font-medium">
                              <User className="h-3.5 w-3.5 inline mr-1.5" />
                              Last name <span className="text-red-500">*</span>
                            </Label>
                            <Input
                              id="last_name"
                              name="last_name"
                              value={formData.last_name}
                              onChange={handleInputChange}
                              required
                              placeholder="Enter your last name"
                              className="border-muted-foreground/20"
                            />
                          </div>
                        </div>

                        <div className="space-y-1.5">
                          <Label htmlFor="email" className="text-sm font-medium">
                            <Mail className="h-3.5 w-3.5 inline mr-1.5" />
                            Email <span className="text-red-500">*</span>
                          </Label>
                          <Input
                            id="email"
                            name="email"
                            type="email"
                            value={formData.email}
                            onChange={handleInputChange}
                            required
                            placeholder="your.email@example.com"
                            className="border-muted-foreground/20"
                          />
                        </div>

                        <div className="flex justify-between mt-4">
                          <div></div>
                          <Button
                            type="button"
                            onClick={() => setActiveTab("company")}
                            className="gap-2"
                          >
                            Next: Company Details
                            <ChevronRight className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </TabsContent>

                    <TabsContent value="company" className="mt-0">
                      <div className="space-y-4">
                        <div className="border rounded-lg p-5 bg-muted/30">
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                              <Label htmlFor="company" className="text-sm font-medium">
                                <Briefcase className="h-3.5 w-3.5 inline mr-1.5" />
                                Company name
                              </Label>
                              <Input
                                id="company"
                                name="company"
                                value={formData.company || ""}
                                onChange={handleInputChange}
                                placeholder="Enter company name"
                                className="border-muted-foreground/20"
                              />
                            </div>
                            <div className="space-y-1.5">
                              <Label htmlFor="title" className="text-sm font-medium">
                                <Briefcase className="h-3.5 w-3.5 inline mr-1.5" />
                                Job title
                              </Label>
                              <Input
                                id="title"
                                name="title"
                                value={formData.title || ""}
                                onChange={handleInputChange}
                                placeholder="Enter job title"
                                className="border-muted-foreground/20"
                              />
                            </div>
                          </div>
                        </div>

                        <div className="space-y-1.5">
                          <Label htmlFor="website" className="text-sm font-medium">
                            <Globe className="h-3.5 w-3.5 inline mr-1.5" />
                            Website
                          </Label>
                          <Input
                            id="website"
                            name="website"
                            type="url"
                            value={formData.website || ""}
                            onChange={handleInputChange}
                            placeholder="https://www.example.com"
                            className="border-muted-foreground/20"
                          />
                        </div>

                        <div className="space-y-1.5">
                          <Label htmlFor="notes" className="text-sm font-medium">
                            <FileText className="h-3.5 w-3.5 inline mr-1.5" />
                            Notes
                          </Label>
                          <Textarea
                            id="notes"
                            name="notes"
                            value={formData.notes || ""}
                            onChange={handleInputChange}
                            placeholder="Enter any additional notes or bio information"
                            className="h-24 resize-none border-muted-foreground/20"
                          />
                        </div>

                        <div className="flex justify-between mt-4">
                          <Button
                            type="button"
                            variant="outline"
                            onClick={() => setActiveTab("personal")}
                          >
                            Back
                          </Button>
                          <Button
                            type="button"
                            onClick={() => setActiveTab("contact")}
                            className="gap-2"
                          >
                            Next: Contact Info
                            <ChevronRight className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </TabsContent>

                    <TabsContent value="contact" className="mt-0">
                      <div className="space-y-4">
                        <div className="border rounded-lg p-5 bg-muted/30">
                          <h3 className="text-sm font-medium mb-4 flex items-center">
                            <Phone className="h-4 w-4 mr-2 text-primary" />
                            Phone Numbers
                          </h3>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                              <Label htmlFor="mobile_number" className="text-sm font-medium">
                                Mobile Number <span className="text-red-500">*</span>
                              </Label>
                              <PhoneNumberInput
                                id="mobile_number"
                                name="mobile_number"
                                value={formData.mobile_number || ""}
                                onChange={handlePhoneChange('mobile_number')}
                                placeholder="XXXXX XXXXX"
                                required
                                hideLabel
                              />
                            </div>
                            <div className="space-y-1.5">
                              <Label htmlFor="work_number" className="text-sm font-medium">
                                Work Number
                              </Label>
                              <PhoneNumberInput
                                id="work_number"
                                name="work_number"
                                value={formData.work_number || ""}
                                onChange={handlePhoneChange('work_number')}
                                placeholder="XXXXX XXXXX"
                                hideLabel
                              />
                            </div>
                          </div>
                        </div>

                        <div className="border rounded-lg p-5 bg-muted/30">
                          <h3 className="text-sm font-medium mb-4 flex items-center">
                            <MapPin className="h-4 w-4 mr-2 text-primary" />
                            Address Information
                          </h3>

                          <div className="flex items-center justify-between mb-4 p-3 bg-gray-50 rounded-md border">
                            <div className="flex items-center space-x-2">
                              {useDefaultAddress ?
                                <ToggleRight className="h-5 w-5 text-primary" /> :
                                <ToggleLeft className="h-5 w-5 text-gray-400" />}
                              <span className="text-sm font-medium">Use default address: Phonon HQ</span>
                            </div>
                            <Switch
                              checked={useDefaultAddress}
                              onCheckedChange={setUseDefaultAddress}
                              aria-label="Toggle default address"
                            />
                          </div>

                          <div className="space-y-4" style={{ opacity: useDefaultAddress ? 0.5 : 1 }}>
                            <div className="space-y-1.5">
                              <Label htmlFor="address.street" className="text-sm font-medium">
                                Street Address
                              </Label>
                              <Input
                                id="address.street"
                                name="address.street"
                                value={formData.address?.street || ""}
                                onChange={handleInputChange}
                                placeholder="123 Main Street"
                                className="border-muted-foreground/20"
                              />
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                              <div className="space-y-1.5">
                                <Label htmlFor="address.city" className="text-sm font-medium">
                                  City
                                </Label>
                                <Input
                                  id="address.city"
                                  name="address.city"
                                  value={formData.address?.city || ""}
                                  onChange={handleInputChange}
                                  placeholder="City"
                                  className="border-muted-foreground/20"
                                  disabled={useDefaultAddress}
                                />
                              </div>
                              <div className="space-y-1.5">
                                <Label htmlFor="address.state" className="text-sm font-medium">
                                  State/Province
                                </Label>
                                <Input
                                  id="address.state"
                                  name="address.state"
                                  value={formData.address?.state || ""}
                                  onChange={handleInputChange}
                                  placeholder="State or Province"
                                  className="border-muted-foreground/20"
                                  disabled={useDefaultAddress}
                                />
                              </div>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                              <div className="space-y-1.5">
                                <Label htmlFor="address.zip_code" className="text-sm font-medium">
                                  Postal/ZIP Code
                                </Label>
                                <Input
                                  id="address.zip_code"
                                  name="address.zip_code"
                                  value={formData.address?.zip_code || ""}
                                  onChange={handleInputChange}
                                  placeholder="ZIP or Postal Code"
                                  className="border-muted-foreground/20"
                                  disabled={useDefaultAddress}
                                />
                              </div>
                              <div className="space-y-1.5">
                                <Label htmlFor="address.country" className="text-sm font-medium">
                                  Country
                                </Label>
                                <Input
                                  id="address.country"
                                  name="address.country"
                                  value={formData.address?.country || ""}
                                  onChange={handleInputChange}
                                  placeholder="Country"
                                  className="border-muted-foreground/20"
                                  disabled={useDefaultAddress}
                                />
                              </div>
                            </div>
                          </div>
                        </div>

                        <div className="flex justify-between mt-6">
                          <Button
                            type="button"
                            variant="outline"
                            onClick={() => setActiveTab("company")}
                          >
                            Back
                          </Button>
                          <Button
                            type="submit"
                            disabled={loading || !isFormComplete()}
                            className="gap-2 bg-primary hover:bg-primary/90 text-white"
                          >
                            {loading ? (
                              <>
                                <span className="animate-spin">
                                  <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                  </svg>
                                </span>
                                Generating...
                              </>
                            ) : (
                              <>
                                <PlusCircle className="h-4 w-4" />
                                Generate QR Code
                              </>
                            )}
                          </Button>
                        </div>
                      </div>
                    </TabsContent>
                  </div>
                </Tabs>
              </form>
            </CardContent>
          </Card>

          <Card className="border shadow-sm overflow-hidden">
            <CardHeader className="pb-4 bg-gray-50/80 border-b">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center">
                <div>
                  <CardTitle className="text-xl font-bold">Your QR Codes</CardTitle>
                  <CardDescription className="text-muted-foreground mt-1">
                    Manage and track your generated QR codes
                  </CardDescription>
                </div>
                <Badge variant="outline" className="mt-2 sm:mt-0 flex items-center gap-1.5 bg-white">
                  <QrCode className="h-3.5 w-3.5" />
                  QR Collection
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-6 px-6 pb-0">
              <QRCodeList
                ref={qrListRef}
                onEdit={handleEdit}
                onShare={handleShare}
                showAnalytics={true}
              />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}