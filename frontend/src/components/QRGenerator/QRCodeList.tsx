"use client"

import * as React from 'react'
import { useState, useEffect } from 'react'
import { Card, CardContent } from '../ui/card'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { 
  Download, 
  Edit, 
  Trash2, 
  Loader2, 
  AlertCircle,
  QrCode,
  ChevronDown,
  Share2,
  BarChart2
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'
import { qrService } from '@/services/api'
import { toast } from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'

interface QRCode {
  id: string
  user_id: string
  object_name: string
  qr_image_url: string
  created_at: string
  updated_at: string
  total_scans: number
  type: string
  vcard_id: string
  tracking_id?: string
  metadata?: {
    vcard_id?: string
    vcard_name?: string
    firstName?: string
    lastName?: string
    [key: string]: any
  }
}

interface QRCodeListProps {
  onEdit?: (qrCode: QRCode) => void
  onShare?: (qrCode: QRCode) => void
  showAnalytics?: boolean
  className?: string
}

const QRCodeList = React.forwardRef<{ refreshList: () => void }, QRCodeListProps>(({ 
  onEdit, 
  onShare,
  showAnalytics = true,
  className = ''
}, ref) => {
  const navigate = useNavigate()
  const [qrCodes, setQrCodes] = useState<QRCode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('all')
  const [sortBy, setSortBy] = useState('newest')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    fetchQRCodes()
  }, [])

  const fetchQRCodes = async () => {
    try {
      setError(null)
      const codes = await qrService.listQRCodes()
      setQrCodes(codes)
    } catch (error) {
      console.error('Failed to fetch QR codes:', error)
      setError('Failed to load QR codes. Please try again later.')
    } finally {
      setLoading(false)
    }
  }

  React.useImperativeHandle(ref, () => ({
    refreshList: fetchQRCodes
  }))

  const addQRCode = (newQRCode: QRCode) => {
    setQrCodes(prevCodes => [newQRCode, ...prevCodes])
    fetchQRCodes()
  }

  const updateQRCode = (updatedQRCode: QRCode) => {
    setQrCodes(prevCodes => 
      prevCodes.map(code => 
        code.id === updatedQRCode.id ? updatedQRCode : code
      )
    )
  }

  const removeQRCode = (id: string) => {
    setQrCodes(prevCodes => prevCodes.filter(code => code.id !== id))
  }

  const handleDownload = async (qrCode: QRCode, format: 'png' | 'svg' | 'pdf' = 'png') => {
    try {
      const response = await fetch(qrCode.qr_image_url)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `qr-code-${qrCode.tracking_id}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      toast.success(`QR code downloaded as ${format.toUpperCase()}`)
    } catch (error) {
      console.error('Failed to download QR code:', error)
      toast.error('Failed to download QR code')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await qrService.deleteQRCode(id)
      removeQRCode(id)
      toast.success('QR code deleted successfully')
    } catch (error) {
      console.error('Failed to delete QR code:', error)
      toast.error('Failed to delete QR code')
      fetchQRCodes()
    }
  }

  const handleViewAnalytics = (qrCode: QRCode) => {
    console.log('QR Code data:', qrCode);
    if (qrCode.id) {
      navigate(`/analytics/qr/${qrCode.id}`);
    } else {
      console.error('Missing QR code ID:', qrCode);
      toast.error('Analytics not available for this QR code');
    }
  }

  const filteredAndSortedQRCodes = React.useMemo(() => {
    let filtered = [...qrCodes]
    
    if (filter !== 'all') {
      filtered = filtered.filter(qr => qr.type === filter)
    }
    
    if (searchQuery) {
      const searchLower = searchQuery.toLowerCase()
      filtered = filtered.filter(qr => 
        qr.id.toLowerCase().includes(searchLower) ||
        qr.type.toLowerCase().includes(searchLower) ||
        qr.metadata?.firstName?.toLowerCase().includes(searchLower) ||
        qr.metadata?.lastName?.toLowerCase().includes(searchLower) ||
        qr.metadata?.vcard_name?.toLowerCase().includes(searchLower)
      )
    }
    
    filtered.sort((a, b) => {
      if (sortBy === 'newest') {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      } else if (sortBy === 'oldest') {
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      } else if (sortBy === 'most_scanned') {
        return b.total_scans - a.total_scans
      } else if (sortBy === 'name') {
        const nameA = a.metadata?.vcard_name || a.metadata?.firstName || ''
        const nameB = b.metadata?.vcard_name || b.metadata?.firstName || ''
        return nameA.localeCompare(nameB)
      }
      return 0
    })
    
    return filtered
  }, [qrCodes, filter, sortBy, searchQuery])

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
    <div className={`space-y-6 ${className}`}>
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Your QR Codes</h2>
      </div>

      <div className="flex flex-col sm:flex-row justify-between gap-4">
        <div className="flex flex-1 gap-4">
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="vcard">VCard</SelectItem>
              <SelectItem value="url">URL</SelectItem>
              <SelectItem value="pdf">PDF</SelectItem>
            </SelectContent>
          </Select>
          
          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="newest">Newest First</SelectItem>
              <SelectItem value="oldest">Oldest First</SelectItem>
              <SelectItem value="most_scanned">Most Scanned</SelectItem>
              <SelectItem value="name">By Name</SelectItem>
            </SelectContent>
          </Select>
        </div>
        
        <div className="flex-1">
          <Input
            placeholder="Search QR codes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredAndSortedQRCodes.map((qr) => (
          <Card key={qr.id} className="overflow-hidden">
            <CardContent className="p-6">
              <div className="relative">
                <img
                  src={qr.qr_image_url}
                  alt="QR Code"
                  className="w-full aspect-square object-contain mb-4"
                />
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <h3 className="font-semibold">
                    {qr.metadata?.vcard_name || 
                     `${qr.metadata?.firstName || ''} ${qr.metadata?.lastName || ''}`.trim() ||
                     qr.type.charAt(0).toUpperCase() + qr.type.slice(1)}
                  </h3>
                  <span className="text-sm text-gray-500">
                    {qr.total_scans} scans
                  </span>
                </div>
                <p className="text-sm text-gray-500">
                  Created {new Date(qr.created_at).toLocaleDateString()}
                </p>
                
                <div className="flex gap-2 mt-4">
                  {onEdit && (
                    <Button variant="outline" size="sm" onClick={() => onEdit(qr)}>
                      <Edit className="h-4 w-4" />
                    </Button>
                  )}
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="outline" size="sm">
                        <Download className="h-4 w-4 mr-1" />
                        <ChevronDown className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent>
                      <DropdownMenuItem onClick={() => handleDownload(qr, 'png')}>
                        Download PNG
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleDownload(qr, 'svg')}>
                        Download SVG
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleDownload(qr, 'pdf')}>
                        Download PDF
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                  {onShare && (
                    <Button variant="outline" size="sm" onClick={() => onShare(qr)}>
                      <Share2 className="h-4 w-4" />
                    </Button>
                  )}
                  {showAnalytics && (
                    <Button variant="outline" size="sm" onClick={() => handleViewAnalytics(qr)}>
                      <BarChart2 className="h-4 w-4" />
                    </Button>
                  )}
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => handleDelete(qr.id)}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredAndSortedQRCodes.length === 0 && (
        <div className="text-center py-10">
          <QrCode className="h-12 w-12 mx-auto mb-4 text-gray-400" />
          <p className="text-gray-500">No QR codes found</p>
        </div>
      )}
    </div>
  )
})

export default QRCodeList 