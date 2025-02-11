"use client"

import * as React from 'react'
import { useState, useEffect } from 'react'
import { Card, CardContent } from '../ui/card'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'
import { MoreHorizontal, Download, Edit, Trash2 } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu'
import { qrService } from '@/services/api'
import { toast } from 'react-hot-toast'

interface QRCode {
  id: string
  tracking_id: string
  qr_image: string
  qr_image_url: string
  created_at: string
  type: string
  total_scans: number
  metadata: {
    vcard_id?: string
    [key: string]: any
  }
}

export default function QRCodeList() {
  const [qrCodes, setQrCodes] = useState<QRCode[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [sortBy, setSortBy] = useState('newest')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    fetchQRCodes()
  }, [])

  const fetchQRCodes = async () => {
    try {
      const codes = await qrService.listQRCodes()
      setQrCodes(codes)
    } catch (error) {
      console.error('Failed to fetch QR codes:', error)
      toast.error('Failed to load QR codes')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async (qrCode: QRCode) => {
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
    } catch (error) {
      console.error('Failed to download QR code:', error);
      toast.error('Failed to download QR code');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await qrService.deleteQRCode(id)
      toast.success('QR code deleted successfully')
      fetchQRCodes()
    } catch (error) {
      console.error('Failed to delete QR code:', error)
      toast.error('Failed to delete QR code')
    }
  }

  const filteredAndSortedQRCodes = React.useMemo(() => {
    let filtered = [...qrCodes]
    
    // Apply type filter
    if (filter !== 'all') {
      filtered = filtered.filter(qr => qr.type === filter)
    }
    
    // Apply search
    if (searchQuery) {
      filtered = filtered.filter(qr => 
        qr.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        qr.type.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }
    
    // Apply sorting
    filtered.sort((a, b) => {
      if (sortBy === 'newest') {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      } else if (sortBy === 'oldest') {
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      } else if (sortBy === 'most_scanned') {
        return b.total_scans - a.total_scans
      }
      return 0
    })
    
    return filtered
  }, [qrCodes, filter, sortBy, searchQuery])

  if (loading) {
    return <div>Loading...</div>
  }

  return (
    <div className="space-y-6">
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
                <div className="absolute top-0 right-0 m-2">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent>
                      <DropdownMenuItem onClick={() => handleDownload(qr)}>
                        <Download className="mr-2 h-4 w-4" />
                        Download
                      </DropdownMenuItem>
                      <DropdownMenuItem>
                        <Edit className="mr-2 h-4 w-4" />
                        Edit
                      </DropdownMenuItem>
                      <DropdownMenuItem 
                        className="text-red-600"
                        onClick={() => handleDelete(qr.id)}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <h3 className="font-semibold">
                    {qr.type.charAt(0).toUpperCase() + qr.type.slice(1)}
                  </h3>
                  <span className="text-sm text-gray-500">
                    {qr.total_scans} scans
                  </span>
                </div>
                <p className="text-sm text-gray-500">
                  Created {new Date(qr.created_at).toLocaleDateString()}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredAndSortedQRCodes.length === 0 && (
        <div className="text-center py-10">
          <p className="text-gray-500">No QR codes found</p>
        </div>
      )}
    </div>
  )
} 