"use client"

import * as React from 'react'
import { useState, useEffect } from 'react'
import { Button } from "../ui/button"
import { Input } from "../ui/input"
import { Label } from "../ui/label"
import { Textarea } from "../ui/textarea"
import { Card, CardContent } from "../ui/card"
import { toast } from 'react-hot-toast'
import { qrService } from '@/services/api'
import type { QRCodeResponse, VCardData, QRDesignOptions } from '@/types/api'
import { ArrowLeft } from 'lucide-react'
import QRDesignDialog from './QRDesignDialog'
import { useDebounce } from '../../hooks/useDebounce'
import { api } from '../../services/api'

interface Props {
  qrCode: QRCodeResponse
  onUpdate: () => void
  onBack: () => void
}

const DEFAULT_DESIGN: QRDesignOptions = {
  pattern_style: 'square',
  eye_style: 'square',
  foreground_color: '#000000',
  background_color: '#FFFFFF',
  logo_background: false,
  logo_round: true,
  logo_size: 0.25,
  error_correction: 'H',
  box_size: 10,
  border: 4
}

const PATTERNS = [
  { id: 'square', label: 'Square', icon: '⬛' },
  { id: 'rounded', label: 'Rounded', icon: '🔲' },
  { id: 'dots', label: 'Dots', icon: '⚫' },
  { id: 'gapped', label: 'Gapped', icon: '⬚' },
  { id: 'vertical', label: 'Vertical', icon: '▤' },
  { id: 'horizontal', label: 'Horizontal', icon: '▥' }
]

const EYE_STYLES = [
  { id: 'square', label: 'Square' },
  { id: 'circle', label: 'Circle' }
]

export default function QRCodeEditor({ qrCode, onUpdate, onBack }: Props) {
  const [loading, setLoading] = useState(false)
  const [showDesignDialog, setShowDesignDialog] = useState(false)
  const [formData, setFormData] = useState<VCardData>({
    first_name: '',
    last_name: '',
    email: '',
    mobile_number: '',
    work_number: '',
    company: '',
    title: '',
    website: '',
    address: {
      street: '',
      city: '',
      state: '',
      country: '',
      zip_code: ''
    },
    notes: ''
  })
  const [design, setDesign] = useState<QRDesignOptions>(qrCode.design || DEFAULT_DESIGN)
  const [previewUrl, setPreviewUrl] = useState<string>('')
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const debouncedDesign = useDebounce(design, 500)

  useEffect(() => {
    // Load initial data from qrCode
    if (qrCode && qrCode.metadata) {
      console.log('QR Code metadata:', qrCode.metadata)
      const vcardId = qrCode.metadata.vcard_id
      
      if (!vcardId) {
        console.error('No VCard ID found in QR code metadata:', qrCode.metadata)
        toast.error('Invalid QR code data')
        return
      }

      console.log('Loading VCard data with ID:', vcardId)
      loadVCardData(vcardId)
    } else {
      console.error('Invalid QR code data:', qrCode)
      toast.error('Invalid QR code data')
    }
  }, [qrCode])

  useEffect(() => {
    const generatePreview = async () => {
      try {
        const response = await api.post(`/qrcodes/preview`, {
          vcard_id: qrCode.metadata.vcard_id,
          design: debouncedDesign
        })
        setPreviewUrl(response.data.preview_url)
      } catch (error) {
        console.error('Failed to generate preview:', error)
      }
    }

    generatePreview()
  }, [debouncedDesign, qrCode.metadata.vcard_id])

  const loadVCardData = async (vcardId: string) => {
    try {
      if (!vcardId) {
        console.error('No VCard ID provided')
        toast.error('Invalid QR code data')
        return
      }

      console.log('Fetching VCard data for ID:', vcardId)
      const response = await qrService.getVCard(vcardId)
      console.log('VCard data received:', response)
      
      if (!response || !response._id) {
        console.error('Invalid VCard data received:', response)
        toast.error('Failed to load contact information')
        return
      }

      // Always use MongoDB _id as vcard_id
      const formattedData = {
        ...response,
        vcard_id: response._id
      }
      console.log('Setting form data:', formattedData)
      setFormData(formattedData)
    } catch (error: any) {
      console.error('Failed to load VCard data:', error)
      
      // Handle specific error cases
      if (error?.response?.status === 400) {
        toast.error('Invalid QR code data')
      } else if (error?.response?.status === 404) {
        toast.error('Contact information not found')
      } else {
        toast.error('Failed to load contact information')
      }
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    if (name.includes('.')) {
      // Handle nested address fields
      const [parent, child] = name.split('.')
      setFormData(prev => ({
        ...prev,
        [parent]: {
          ...(prev[parent as keyof VCardData] as Record<string, string>),
          [child]: value
        }
      }))
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }))
    }
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        toast.error('Image size should be less than 5MB')
        return
      }

      const reader = new FileReader()
      reader.onloadend = () => {
        setFormData(prev => ({
          ...prev,
          profile_picture: reader.result as string
        }))
      }
      reader.readAsDataURL(file)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      console.log('Submitting form data:', formData)
      await qrService.updateQRCode(qrCode.id, {
        ...formData,
        vcard_id: formData.vcard_id || qrCode.metadata.vcard_id // Ensure we have the VCard ID
      })
      toast.success('QR code updated successfully')
      onUpdate()
    } catch (error) {
      console.error('Failed to update QR code:', error)
      toast.error('Failed to update QR code')
    } finally {
      setLoading(false)
    }
  }

  const handleDesignApply = async (design: QRDesignOptions, templateId?: string) => {
    setLoading(true)
    try {
      await qrService.updateQRCodeWithDesign(qrCode.id, {
        ...formData,
        vcard_id: formData.vcard_id || qrCode.metadata.vcard_id,
        design,
        template_id: templateId
      })
      toast.success('QR code design updated successfully')
      onUpdate()
    } catch (error) {
      console.error('Failed to update QR code design:', error)
      toast.error('Failed to update QR code design')
    } finally {
      setLoading(false)
    }
  }

  const handleLogoChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      if (file.size > 1024 * 1024) { // 1MB limit
        alert('Logo file size must be less than 1MB')
        return
      }
      setLogoFile(file)
      
      // Upload logo and get URL
      const formData = new FormData()
      formData.append('logo', file)
      try {
        const response = await api.post('/qrcodes/upload-logo', formData)
        setDesign(prev => ({
          ...prev,
          logo_url: response.data.logo_url
        }))
      } catch (error) {
        console.error('Failed to upload logo:', error)
      }
    }
  }

  const handleSave = () => {
    handleDesignApply(design)
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={onBack}
            className="hover:bg-gray-100"
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h2 className="text-2xl font-bold">Edit QR Code</h2>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            disabled={loading}
            onClick={() => setShowDesignDialog(true)}
          >
            Change design
          </Button>
          <Button variant="outline" disabled={loading}>
            Save as template
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* QR Code Preview */}
        <Card>
          <CardContent className="p-6">
            <div className="aspect-square relative">
              {previewUrl ? (
                <img
                  src={previewUrl}
                  alt="QR Code"
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="w-full aspect-square bg-gray-100 animate-pulse rounded" />
              )}
            </div>
          </CardContent>
        </Card>

        {/* Edit Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="first_name">First name</Label>
              <Input
                id="first_name"
                name="first_name"
                value={formData.first_name}
                onChange={handleInputChange}
                required
              />
            </div>
            <div className="space-y-2">
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

          <div className="space-y-2">
            <Label htmlFor="profile_picture">Profile photo</Label>
            <Input
              id="profile_picture"
              name="profile_picture"
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              className="cursor-pointer"
            />
            {formData.profile_picture && (
              <div className="mt-2">
                <img
                  src={formData.profile_picture}
                  alt="Profile Preview"
                  className="w-24 h-24 object-cover rounded-full"
                />
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="mobile_number">Mobile number</Label>
            <Input
              id="mobile_number"
              name="mobile_number"
              value={formData.mobile_number || ''}
              onChange={handleInputChange}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="work_number">Phone number</Label>
            <Input
              id="work_number"
              name="work_number"
              value={formData.work_number || ''}
              onChange={handleInputChange}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="website">Website</Label>
            <Input
              id="website"
              name="website"
              value={formData.website || ''}
              onChange={handleInputChange}
            />
          </div>

          <div className="space-y-2">
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

          <div className="space-y-2">
            <Label htmlFor="company">Company name</Label>
            <Input
              id="company"
              name="company"
              value={formData.company || ''}
              onChange={handleInputChange}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="title">Job title</Label>
            <Input
              id="title"
              name="title"
              value={formData.title || ''}
              onChange={handleInputChange}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="address.street">Street</Label>
            <Input
              id="address.street"
              name="address.street"
              value={formData.address?.street || ''}
              onChange={handleInputChange}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="address.city">City</Label>
              <Input
                id="address.city"
                name="address.city"
                value={formData.address?.city || ''}
                onChange={handleInputChange}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="address.state">State</Label>
              <Input
                id="address.state"
                name="address.state"
                value={formData.address?.state || ''}
                onChange={handleInputChange}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="address.country">Country</Label>
              <Input
                id="address.country"
                name="address.country"
                value={formData.address?.country || ''}
                onChange={handleInputChange}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="address.zip_code">Post code</Label>
              <Input
                id="address.zip_code"
                name="address.zip_code"
                value={formData.address?.zip_code || ''}
                onChange={handleInputChange}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="notes">Description</Label>
            <Textarea
              id="notes"
              name="notes"
              value={formData.notes || ''}
              onChange={handleInputChange}
              rows={4}
            />
          </div>

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Saving changes...' : 'Save changes'}
          </Button>
        </form>
      </div>

      {qrCode.metadata.vcard_id && (
        <QRDesignDialog
          isOpen={showDesignDialog}
          onClose={() => setShowDesignDialog(false)}
          onApply={handleDesignApply}
          initialDesign={design}
          vcardId={qrCode.metadata.vcard_id}
        />
      )}
    </div>
  )
} 