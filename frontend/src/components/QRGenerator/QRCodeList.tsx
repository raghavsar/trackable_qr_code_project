"use client"

import * as React from 'react'
import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader } from '../ui/card'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { 
  Download, 
  Edit, 
  Trash2, 
  Loader2, 
  AlertCircle,
  QrCode,
  Share2,
  BarChart2,
  Calendar,
  Scan
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
import { Badge } from "../ui/badge"

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
      
      // Transform the data to ensure vcard_id is available at the root level
      const transformedCodes = codes.map(code => {
        // Use root level vcard_id if it exists, otherwise try to get it from metadata
        const vcardId = code.vcard_id || (code.metadata && code.metadata.vcard_id) || '';
        
        return {
          ...code,
          vcard_id: vcardId
        };
      });
      
      setQrCodes(transformedCodes as QRCode[]);
      
      // Debug log for VCard IDs
      console.log('QR Codes with VCard IDs:', transformedCodes.map(code => ({
        id: code.id,
        vcard_id: code.vcard_id,
        has_valid_vcard_id: !!code.vcard_id && /^[0-9a-fA-F]{24}$/.test(code.vcard_id)
      })))
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
    console.log('QR Code data for analytics:', qrCode);
    
    // Get vcard_id from either the root level or metadata
    const vcardId = qrCode.vcard_id || (qrCode.metadata && qrCode.metadata.vcard_id);
    
    // Check if vcard_id exists
    if (!vcardId) {
      console.error('Missing VCard ID in QR code data:', qrCode);
      toast.error('Analytics not available: Missing VCard ID');
      return;
    }
    
    // Navigate to analytics page with the vcard_id
    console.log('Navigating to analytics for VCard ID:', vcardId);
    navigate(`/analytics/vcard/${vcardId}`);
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
      <div className="flex flex-col sm:flex-row justify-between gap-4 pb-2">
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
          <Card 
            key={qr.id} 
            className="overflow-hidden shadow-sm hover:shadow transition-shadow border-gray-200"
          >
            <CardHeader className="pb-2 pt-3 px-4 border-b bg-gray-50/60">
              <div className="flex justify-between items-start">
                <Badge variant="outline" className="text-xs font-normal bg-white">
                  {qr.type.toUpperCase()}
                </Badge>
                <Badge className="bg-primary/10 text-primary border-0 flex items-center gap-1">
                  <Scan className="h-3 w-3" />
                  {qr.total_scans} scans
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="px-4 pt-3 pb-4">
              <div className="relative bg-white rounded-md p-3 mb-3 border">
                <div className="aspect-square flex items-center justify-center">
                  <img
                    src={qr.qr_image_url}
                    alt="QR Code"
                    className="w-[90%] h-[90%] object-contain"
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <div>
                  <h3 className="font-semibold text-base truncate">
                    {qr.metadata?.vcard_name || 
                     `${qr.metadata?.firstName || ''} ${qr.metadata?.lastName || ''}`.trim() ||
                     qr.type.charAt(0).toUpperCase() + qr.type.slice(1)}
                  </h3>
                  <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                    <Calendar className="h-3 w-3" />
                    Created {new Date(qr.created_at).toLocaleDateString()}
                  </p>
                </div>
                
                <div className="flex gap-2 mt-4 justify-between">
                  <div className="flex gap-1">
                    {onEdit && (
                      <Button variant="outline" size="sm" onClick={() => onEdit(qr)} 
                        className="h-8 w-8 p-0 border-gray-200">
                        <Edit className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="outline" size="sm" className="h-8 w-8 p-0 border-gray-200">
                          <Download className="h-3.5 w-3.5" />
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
                      <Button variant="outline" size="sm" onClick={() => onShare(qr)} 
                        className="h-8 w-8 p-0 border-gray-200">
                        <Share2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                  <div className="flex gap-1">
                    {showAnalytics && (
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => handleViewAnalytics(qr)}
                        disabled={!(qr.vcard_id || (qr.metadata && qr.metadata.vcard_id))}
                        title={!(qr.vcard_id || (qr.metadata && qr.metadata.vcard_id)) ? 
                          "Analytics not available: Missing VCard ID" : "View analytics"}
                        className="h-8 w-8 p-0 text-blue-600 hover:text-blue-700 hover:bg-blue-50 border-blue-200"
                      >
                        <BarChart2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => handleDelete(qr.id)}
                      className="h-8 w-8 p-0 text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredAndSortedQRCodes.length === 0 && (
        <Card className="bg-muted/20 border-dashed">
          <CardContent className="p-6">
            <div className="flex flex-col items-center justify-center text-center py-8">
              <div className="p-4 bg-muted/30 rounded-full mb-4">
                <QrCode className="h-12 w-12 text-muted-foreground opacity-70" />
              </div>
              <h3 className="text-lg font-medium mb-2">No QR Codes Found</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto mb-6">
                {searchQuery || filter !== 'all' ? 
                  "Try adjusting your search or filters to find what you're looking for." : 
                  "You haven't created any QR codes yet. Fill out the form above to get started."}
              </p>
              {(searchQuery || filter !== 'all') && (
                <Button variant="outline" onClick={() => {
                  setSearchQuery('');
                  setFilter('all');
                }}>
                  Clear Filters
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
})

export default QRCodeList