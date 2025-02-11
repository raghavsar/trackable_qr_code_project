"use client"

import { useState, useEffect } from 'react'
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { 
  Edit2, 
  Download,
  ChevronDown,
  Loader2,
  AlertCircle,
  QrCode,
  FileText,
  Link2,
  Contact2
} from 'lucide-react'
import { qrService } from '@/services/api'
import type { QRCodeResponse } from '@/types/api'
import { Input } from "@/components/ui/input"
import { useAuth } from '@/hooks/useAuth'
import { toast } from 'react-hot-toast'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export default function GeneratedQRList() {
  const { user } = useAuth()
  const [qrCodes, setQrCodes] = useState<QRCodeResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('all')
  const [sortBy, setSortBy] = useState('newest')

  useEffect(() => {
    loadQRCodes()
  }, [])

  const loadQRCodes = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await qrService.listQRCodes()
      setQrCodes(response || [])
    } catch (error) {
      console.error('Failed to load QR codes:', error)
      setError('Failed to load QR codes. Please try again later.')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async (qrCode: QRCodeResponse) => {
    try {
      const response = await fetch(qrCode.qr_image_url);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `qr-code-${qrCode.tracking_id}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success('QR code downloaded successfully');
    } catch (error) {
      console.error('Failed to download QR code:', error);
      toast.error('Failed to download QR code');
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'vcard':
        return <Contact2 className="h-4 w-4" />
      case 'landing':
        return <FileText className="h-4 w-4" />
      case 'short-link':
        return <Link2 className="h-4 w-4" />
      default:
        return <QrCode className="h-4 w-4" />
    }
  }

  const filteredAndSortedQRCodes = qrCodes
    .filter(qr => {
      if (filterType !== 'all' && qr.type !== filterType) return false
      if (searchQuery) {
        const searchLower = searchQuery.toLowerCase()
        return (
          qr.metadata?.firstName?.toLowerCase().includes(searchLower) ||
          qr.metadata?.lastName?.toLowerCase().includes(searchLower) ||
          qr.tracking_id.toLowerCase().includes(searchLower)
        )
      }
      return true
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'oldest':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        case 'name':
          return (a.metadata?.firstName || '').localeCompare(b.metadata?.firstName || '')
        default: // newest
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      }
    })

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-red-500">
        <AlertCircle className="h-6 w-6 mr-2" />
        <span>{error}</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with filters */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="w-[100px]">
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="vcard">VCard</SelectItem>
              <SelectItem value="landing">Landing</SelectItem>
              <SelectItem value="short-link">Short Link</SelectItem>
            </SelectContent>
          </Select>

          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="newest">Newest first</SelectItem>
              <SelectItem value="oldest">Oldest first</SelectItem>
              <SelectItem value="name">By name</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Input
          type="search"
          placeholder="Search..."
          className="max-w-[300px]"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {/* QR Code Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredAndSortedQRCodes.map((qrCode) => (
          <Card key={qrCode.tracking_id} className="p-4 space-y-4">
            {/* QR Code Image */}
            <div className="bg-gray-50 p-4 rounded-lg flex items-center justify-center">
              <img
                src={qrCode.qr_image_url}
                alt="QR Code"
                className="w-48 h-48 object-contain"
              />
            </div>

            {/* Download Button */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="w-full">
                  <Download className="h-4 w-4 mr-2" />
                  Download QR
                  <ChevronDown className="h-4 w-4 ml-2" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => handleDownload(qrCode)}>
                  Download PNG
                </DropdownMenuItem>
                <DropdownMenuItem>Download SVG</DropdownMenuItem>
                <DropdownMenuItem>Download PDF</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* User Info */}
            <div className="flex items-center justify-center text-sm font-medium">
              {qrCode.metadata?.firstName || 'No name'}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between pt-2 border-t">
              <Button variant="ghost" size="sm" className="text-gray-500">
                <Edit2 className="h-4 w-4 mr-1" />
                Edit
              </Button>
              <div className="flex items-center text-sm text-gray-500">
                <QrCode className="h-4 w-4 mr-1" />
                {qrCode.metadata?.scan_count || 0}
              </div>
            </div>
          </Card>
        ))}
      </div>

      {filteredAndSortedQRCodes.length === 0 && (
        <div className="flex flex-col items-center justify-center h-64 text-gray-500">
          <QrCode className="h-12 w-12 mb-4" />
          <p>No QR codes found</p>
        </div>
      )}
    </div>
  )
} 