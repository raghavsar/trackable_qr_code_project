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
import QRCodeList from './QRCodeList'

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
  const [editingQRCode, setEditingQRCode] = useState<QRCodeResponse | null>(null)

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
      toast.success('QR code generated successfully')
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
      const redirectUrl = `${window.location.origin}/r/${qrCode.vcard_id}`;
      
      if (navigator.share) {
        await navigator.share({
          title: 'My Digital Business Card',
          text: 'Check out my digital business card!',
          url: redirectUrl
        });
      } else {
        await navigator.clipboard.writeText(redirectUrl);
        toast.success('Link copied to clipboard!');
      }
    } catch (error) {
      console.error('Error sharing:', error);
      toast.error('Failed to share QR code');
    }
  };

  const handleDelete = async (code: QRCodeResponse) => {
    try {
      if (!confirm('Are you sure you want to delete this QR code?')) {
        return
      }
      
      await qrService.deleteQRCode(code.id)
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
            <h2 className="text-xl font-semibold mb-6">Create New QR Code</h2>
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

          <QRCodeList 
            onEdit={handleEdit}
            onShare={handleShare}
            showAnalytics={true}
          />
        </>
      )}
    </div>
  )
} 