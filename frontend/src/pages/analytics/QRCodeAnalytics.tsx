"use client"

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { AnalyticsService } from '@/services/api'
import type { AnalyticsData, ScanEvent } from '@/types/analytics'
import { format } from 'date-fns'
import { Loader2, RefreshCw, Smartphone, Globe, ArrowLeft } from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts'
import { useAnalyticsSSE } from '@/hooks/useAnalyticsSSE'

const API_URL = import.meta.env.VITE_API_URL

const analyticsService = new AnalyticsService()

export default function VCardAnalytics() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [timeRange, setTimeRange] = useState('30')
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Get real-time updates with VCard ID
  const { metrics: realtimeMetrics, error: realtimeError, isConnected } = useAnalyticsSSE({ vcardId: id })

  // Initialize metrics with default values
  const metrics = {
    total_scans: realtimeMetrics?.total_scans ?? analytics?.total_scans ?? 0,
    contact_adds: realtimeMetrics?.contact_adds ?? analytics?.contact_adds ?? 0,
    vcf_downloads: realtimeMetrics?.vcf_downloads ?? analytics?.vcf_downloads ?? 0,
    recent_scans: realtimeMetrics?.recent_scans ?? analytics?.recent_scans ?? [],
    scan_history: analytics?.scan_history ?? []
  }

  const fetchAnalytics = async () => {
    if (!id) return
    
    try {
      setLoading(true)
      setError(null)
      console.log('Fetching analytics with timeRange:', timeRange)
      const data = await analyticsService.getVCardAnalytics(id, timeRange)
      console.log('Received analytics data:', data)
      setAnalytics(data)
    } catch (err) {
      console.error('Failed to fetch analytics:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch analytics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAnalytics()
  }, [id, timeRange])

  const handleBack = () => {
    navigate('/analytics')
  }

  const handleRefresh = () => {
    fetchAnalytics()
  }

  // Show connection status
  const renderConnectionStatus = () => (
    <div className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
      isConnected ? 'bg-green-50 text-green-700' : 'bg-yellow-50 text-yellow-700'
    }`}>
      <div className={`w-2 h-2 rounded-full ${
        isConnected ? 'bg-green-500' : 'bg-yellow-500'
      }`} />
      <span>{isConnected ? 'Connected' : 'Connecting...'}</span>
    </div>
  )

  if (loading && !metrics.total_scans && !metrics.recent_scans.length) {
    return (
      <div className="p-8">
        <Button onClick={handleBack} variant="ghost" className="mb-4">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <div className="flex items-center justify-center p-8">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      </div>
    )
  }

  if (error && !metrics.total_scans && !metrics.recent_scans.length) {
    return (
      <div className="p-8">
        <Button onClick={handleBack} variant="ghost" className="mb-4">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
          <span>{error}</span>
          <Button 
            variant="outline" 
            size="sm" 
            className="ml-auto" 
            onClick={handleRefresh}
          >
            <RefreshCw className="h-4 w-4 mr-1" />
            Retry
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <Button onClick={handleBack} variant="ghost">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <h1 className="text-2xl font-bold">VCard Analytics</h1>
        </div>
        <div className="flex items-center gap-2">
          {renderConnectionStatus()}
          <Select 
            value={timeRange} 
            onValueChange={setTimeRange}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select time period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
              <SelectItem value="90">Last 90 days</SelectItem>
            </SelectContent>
          </Select>
          <Button 
            variant="outline" 
            size="icon"
            onClick={handleRefresh}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardHeader className="p-4">
            <CardTitle className="text-sm font-medium text-muted-foreground">TOTAL SCANS</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="text-2xl font-bold">
              {metrics.total_scans}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="p-4">
            <CardTitle className="text-sm font-medium text-muted-foreground">CONTACT ADDS</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="text-2xl font-bold">
              {metrics.contact_adds}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="p-4">
            <CardTitle className="text-sm font-medium text-muted-foreground">VCF DOWNLOADS</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="text-2xl font-bold">
              {metrics.vcf_downloads}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="p-4">
            <CardTitle className="text-sm font-medium text-muted-foreground">MOBILE SCANS</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="text-2xl font-bold">
              {metrics.recent_scans.filter(scan => scan.device_info?.is_mobile).length}
            </div>
          </CardContent>
        </Card>
      </div>

      {metrics.scan_history.length > 0 && (
        <Card>
          <CardContent className="p-6">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={metrics.scan_history}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis 
                  dataKey="date" 
                  className="text-sm text-muted-foreground"
                  tickFormatter={(value) => format(new Date(value), 'MMM dd')}
                />
                <YAxis className="text-sm text-muted-foreground" />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="count" 
                  stroke="hsl(var(--primary))" 
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Recent Scans</h2>
        {metrics.recent_scans.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No recent scans to display
          </div>
        ) : (
          metrics.recent_scans.map((scan, index) => (
            <Card key={index}>
              <CardContent className="p-4 flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-muted rounded-full flex items-center justify-center">
                    {scan.device_info?.is_mobile ? (
                      <Smartphone className="w-4 w-4 text-muted-foreground" />
                    ) : (
                      <Globe className="w-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium">
                      {scan.action_type === 'scan' ? 'Scanned' : 
                       scan.action_type === 'contact_add' ? 'Contact Added' : 
                       scan.action_type === 'vcf_download' ? 'VCF Downloaded' : 
                       'Viewed'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(scan.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="text-sm text-muted-foreground">
                  {scan.device_info?.browser} on {scan.device_info?.os}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  )
} 