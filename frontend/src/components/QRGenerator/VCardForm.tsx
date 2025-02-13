"use client"

import * as React from 'react'
import { useState, useEffect } from "react"
import { Button } from "../ui/button"
import { Input } from "../ui/input"
import { Label } from "../ui/label"
import { CardContent } from "../ui/card"
import { Textarea } from "../ui/textarea"
import { toast } from 'react-hot-toast'
import { qrService } from '@/services/api'
import type { QRCodeResponse, VCardData } from '@/types/api'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "../ui/dropdown-menu"
import { ChevronDown, Download, Edit, Share2, Trash2, BarChart2 } from 'lucide-react'
import QRCodeEditor from './QRCodeEditor'
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

interface FormData {
  first_name: string
  last_name: string
  email: string
  mobile_number: string | undefined
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

export default function VCardForm() {
  const [formData, setFormData] = useState<FormData>({
    first_name: "",
    last_name: "",
    email: "",
    mobile_number: undefined,
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
  const [qrCodes, setQrCodes] = useState<QRCodeResponse[]>([])
  const [loadingQRCodes, setLoadingQRCodes] = useState(false)
  const [editingQRCode, setEditingQRCode] = useState<QRCodeResponse | null>(null)

  const fetchQRCodes = async () => {
    try {
      setLoadingQRCodes(true)
      const codes = await qrService.listQRCodes()
      setQrCodes(codes)
    } catch (error) {
      console.error('Failed to fetch QR codes:', error)
      toast.error('Failed to load QR codes')
    } finally {
      setLoadingQRCodes(false)
    }
  }

  // Fetch QR codes on component mount
  useEffect(() => {
    fetchQRCodes()
  }, [qrCode]) // Refresh when new QR code is generated

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
      // Create VCard first
      const vcard = await qrService.createVCard(formData)
      // Generate QR code with direct vCard data
      const qrCode = await qrService.generateQRCode({
        vcard_id: vcard._id || vcard.id,
        design: {
          pattern_style: 'square',
          eye_style: 'square',
          foreground_color: '#000000',
          background_color: '#FFFFFF',
          error_correction: 'H',
          box_size: 10,
          border: 4
        }
      })
      setQrCode(qrCode)
      toast.success('QR code generated successfully')
      // Refresh QR code list
      fetchQRCodes()
    } catch (error) {
      console.error('Failed to generate QR code:', error)
      toast.error('Failed to generate QR code')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async (qrCode: QRCodeResponse, format: 'png' | 'svg' | 'pdf') => {
    try {
      const url = qrCode.qr_image_url
      const response = await fetch(url)
      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = `qr-code.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(downloadUrl)
    } catch (error) {
      console.error('Failed to download QR code:', error)
      toast.error('Failed to download QR code')
    }
  }

  const handleShare = async (qrCode: QRCodeResponse) => {
    try {
      // Generate the redirect URL
      const redirectUrl = `${window.location.origin}/r/${qrCode.metadata.vcard_id}`;

      // Try Web Share API first
      if (navigator.share) {
        try {
          await navigator.share({
            title: 'My VCard QR Code',
            text: 'Scan this QR code or click to view my contact details',
            url: redirectUrl
          });
          return;
        } catch (shareError) {
          console.log('Web Share API failed, falling back to clipboard', shareError);
        }
      }
      
      // Try Clipboard API next
      if (navigator.clipboard && window.isSecureContext) {
        try {
          await navigator.clipboard.writeText(redirectUrl);
          toast.success('VCard URL copied to clipboard!');
          return;
        } catch (clipboardError) {
          console.log('Clipboard API failed, falling back to manual selection', clipboardError);
        }
      }
      
      // Fallback to manual selection
      const textArea = document.createElement('textarea');
      textArea.value = redirectUrl;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      
      try {
        document.execCommand('copy');
        textArea.remove();
        toast.success('VCard URL copied to clipboard!');
      } catch (fallbackError) {
        console.error('Manual clipboard copy failed', fallbackError);
        textArea.remove();
        toast.error('Failed to copy URL. Please copy it manually: ' + redirectUrl);
      }
    } catch (error) {
      console.error('Failed to share VCard:', error);
      toast.error('Failed to share VCard');
    }
  }

  const handleDelete = async (code: QRCodeResponse) => {
    try {
      if (!confirm('Are you sure you want to delete this QR code?')) {
        return
      }
      
      await qrService.deleteQRCode(code.id)
      setQrCodes(prev => prev.filter(c => c.id !== code.id))
      toast.success('QR code deleted successfully')
    } catch (error) {
      console.error('Failed to delete QR code:', error)
      toast.error('Failed to delete QR code')
    }
  }

  const handleEdit = (code: QRCodeResponse) => {
    setEditingQRCode(code)
  }

  const handleUpdateComplete = () => {
    setEditingQRCode(null)
    // Refresh QR codes list
    fetchQRCodes()
  }

  // Add the analytics handler function
  const handleViewAnalytics = (code: QRCodeResponse) => {
    window.open(`/analytics/qr/${code.id}`, '_blank');
  };

  return (
    <div className="space-y-8">
      {editingQRCode ? (
        <QRCodeEditor 
          qrCode={editingQRCode} 
          onUpdate={handleUpdateComplete}
          onBack={() => setEditingQRCode(null)}
        />
      ) : (
        <>
          <CardContent className="p-4">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Personal Details */}
                <div className="space-y-4">
                  <h2 className="text-lg font-semibold">Personal Details</h2>
                  
                  <div className="space-y-3">
                    <div className="space-y-1.5">
                      <Label>Profile Picture</Label>
                      <div className="flex items-center space-x-4">
                        <Avatar className="w-20 h-20">
                          <AvatarImage src={formData.profile_picture} />
                          <AvatarFallback>
                            {formData.first_name?.[0]}{formData.last_name?.[0]}
                          </AvatarFallback>
                        </Avatar>
                        <Input
                          type="file"
                          accept="image/*"
                          onChange={handleFileChange}
                          className="max-w-[300px]"
                        />
                      </div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <Label htmlFor="first_name">First name</Label>
                      <Input
                        id="first_name"
                        name="first_name"
                        value={formData.first_name}
                        onChange={handleInputChange}
                        required
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="last_name">Last name</Label>
                      <Input
                        id="last_name"
                        name="last_name"
                        value={formData.last_name}
                        onChange={handleInputChange}
                        required
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <Label htmlFor="mobile_number">Mobile Number</Label>
                      <Input
                        id="mobile_number"
                        name="mobile_number"
                        value={formData.mobile_number || ""}
                        onChange={handleInputChange}
                        placeholder="Enter mobile number"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="work_number">Work Number</Label>
                      <Input
                        id="work_number"
                        name="work_number"
                        value={formData.work_number || ""}
                        onChange={handleInputChange}
                        placeholder="Enter work number"
                      />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      name="email"
                      type="email"
                      value={formData.email}
                      onChange={handleInputChange}
                      required
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="website">Website</Label>
                    <Input
                      id="website"
                      name="website"
                      type="url"
                      value={formData.website || ""}
                      onChange={handleInputChange}
                    />
                  </div>
                </div>

                {/* Company Details & Address */}
                <div className="space-y-4">
                  <h2 className="text-lg font-semibold">Company Details</h2>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <Label htmlFor="company">Company name</Label>
                      <Input
                        id="company"
                        name="company"
                        value={formData.company || ""}
                        onChange={handleInputChange}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="title">Job title</Label>
                      <Input
                        id="title"
                        name="title"
                        value={formData.title || ""}
                        onChange={handleInputChange}
                      />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="notes">Notes</Label>
                    <Textarea
                      id="notes"
                      name="notes"
                      value={formData.notes || ""}
                      onChange={handleInputChange}
                      placeholder="Enter any additional notes"
                      className="h-20"
                    />
                  </div>

                  <h2 className="text-lg font-semibold mt-4">Address</h2>
                  <div className="space-y-3">
                    <div className="space-y-1.5">
                      <Label htmlFor="address.street">Street</Label>
                      <Input
                        id="address.street"
                        name="address.street"
                        value={formData.address?.street || ""}
                        onChange={handleInputChange}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <Label htmlFor="address.city">City</Label>
                        <Input
                          id="address.city"
                          name="address.city"
                          value={formData.address?.city || ""}
                          onChange={handleInputChange}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label htmlFor="address.state">State</Label>
                        <Input
                          id="address.state"
                          name="address.state"
                          value={formData.address?.state || ""}
                          onChange={handleInputChange}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <Label htmlFor="address.zip_code">Post code</Label>
                        <Input
                          id="address.zip_code"
                          name="address.zip_code"
                          value={formData.address?.zip_code || ""}
                          onChange={handleInputChange}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label htmlFor="address.country">Country</Label>
                        <Input
                          id="address.country"
                          name="address.country"
                          value={formData.address?.country || ""}
                          onChange={handleInputChange}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-end mt-6">
                <Button type="submit" disabled={loading}>
                  {loading ? "Generating..." : "Generate QR Code"}
                </Button>
              </div>
            </form>
          </CardContent>

          {/* QR Codes List */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">Your QR Codes</h2>
              {loadingQRCodes && (
                <div className="text-sm text-gray-500">Loading...</div>
              )}
            </div>
            
            {qrCodes.length === 0 && !loadingQRCodes ? (
              <div className="text-center py-8 text-gray-500">
                No QR codes generated yet. Create your first VCard above!
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {qrCodes.map((code) => (
                  <div key={code.id} className="bg-white rounded-lg shadow-md p-4 space-y-3">
                    <div className="aspect-square relative">
                      <img
                        src={code.qr_image_url}
                        alt="QR Code"
                        className="w-full h-full object-contain"
                      />
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm font-medium truncate">
                        {code.metadata.vcard_name || 'VCard'}
                      </p>
                      <p className="text-xs text-gray-500">
                        Created: {new Date(code.created_at).toLocaleDateString()}
                      </p>
                      <p className="text-xs text-gray-500">
                        Scans: {code.total_scans}
                      </p>
                    </div>
                    <div className="flex gap-2 justify-end">
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleEdit(code)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="outline" size="sm">
                            <Download className="h-4 w-4 mr-1" />
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent>
                          <DropdownMenuItem onClick={() => handleDownload(code, 'png')}>
                            Download PNG
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleDownload(code, 'svg')}>
                            Download SVG
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleDownload(code, 'pdf')}>
                            Download PDF
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                      <Button variant="outline" size="sm" onClick={() => handleShare(code)}>
                        <Share2 className="h-4 w-4" />
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => handleViewAnalytics(code)}>
                        <BarChart2 className="h-4 w-4" />
                      </Button>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => handleDelete(code)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
} 