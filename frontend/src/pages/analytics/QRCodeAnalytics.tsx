"use client"

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { AnalyticsService } from '@/services/api'
import type { AnalyticsData, ScanEvent } from '@/types/analytics'
import { format, parseISO } from 'date-fns'
import { 
  Loader2, RefreshCw, Smartphone, Globe, ArrowLeft, 
  QrCode, Users, Download, Calendar, Clock, 
  TrendingUp, ExternalLink, CheckCircle2
} from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts'
import { useAnalyticsSSE } from '@/hooks/useAnalyticsSSE'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"

const API_URL = import.meta.env.VITE_API_URL

const analyticsService = new AnalyticsService()

export default function VCardAnalytics() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [timeRange, setTimeRange] = useState('30')
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState("overview")
  
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

  // Calculate mobile scans count (only counting 'scan' action_type)
  const mobileScansCount = metrics.recent_scans.filter(
    scan => scan.device_info?.is_mobile && scan.action_type === 'scan'
  ).length;

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

  // Format date for display
  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'MMM dd, yyyy, h:mm a')
    } catch (e) {
      return dateString
    }
  }

  // Show connection status
  const renderConnectionStatus = () => (
    <Badge variant={isConnected ? "success" : "outline"} className="gap-1.5 ml-2">
      <div className={`w-2 h-2 rounded-full ${
        isConnected ? 'bg-green-500' : 'bg-yellow-500'
      }`} />
      <span>{isConnected ? 'Connected' : 'Connecting...'}</span>
    </Badge>
  )

  // Loading state
  if (loading && !metrics.total_scans && !metrics.recent_scans.length) {
    return (
      <div className="p-8">
        <Button onClick={handleBack} variant="ghost" className="mb-4">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <div className="flex flex-col items-center justify-center p-12 gap-4 text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
          <p className="text-muted-foreground mt-4">Loading analytics data...</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error && !metrics.total_scans && !metrics.recent_scans.length) {
    return (
      <div className="p-8">
        <Button onClick={handleBack} variant="ghost" className="mb-4">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Card className="border-red-200">
          <CardContent className="p-6">
            <div className="flex flex-col items-center justify-center text-center gap-4">
              <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center">
                <ExternalLink className="h-6 w-6 text-red-500" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-red-700 mb-2">Unable to Load Analytics</h3>
                <p className="text-red-600 mb-4">{error}</p>
                <Button 
                  onClick={handleRefresh}
                  variant="outline"
                  className="gap-2"
                >
                  <RefreshCw className="h-4 w-4" />
                  Try Again
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-4 space-y-6 max-w-7xl">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="flex items-center gap-4">
          <Button onClick={handleBack} variant="ghost" size="icon" className="rounded-full">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">VCard Analytics</h1>
            <p className="text-muted-foreground text-sm">Track performance and engagement of your digital business card</p>
          </div>
        </div>
        
        <div className="flex flex-col sm:flex-row items-center gap-2 w-full sm:w-auto">
          {renderConnectionStatus()}
          <div className="flex gap-2 w-full sm:w-auto mt-2 sm:mt-0">
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
              className="flex-shrink-0"
              title="Refresh data"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </div>

      <Tabs defaultValue="overview" className="w-full" onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="activity">Recent Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="border-l-4 border-l-primary shadow-sm hover:shadow transition-shadow">
              <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                  <CardTitle className="text-sm font-medium text-muted-foreground">TOTAL SCANS</CardTitle>
                  <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                    <QrCode className="h-4 w-4 text-primary" />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {metrics.total_scans}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  QR code scans
                </p>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-blue-400 shadow-sm hover:shadow transition-shadow">
              <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                  <CardTitle className="text-sm font-medium text-muted-foreground">MOBILE SCANS</CardTitle>
                  <div className="w-8 h-8 bg-blue-50 rounded-full flex items-center justify-center">
                    <Smartphone className="h-4 w-4 text-blue-500" />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {mobileScansCount}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  From mobile devices
                </p>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-green-400 shadow-sm hover:shadow transition-shadow">
              <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                  <CardTitle className="text-sm font-medium text-muted-foreground">CONTACT ADDS</CardTitle>
                  <div className="w-8 h-8 bg-green-50 rounded-full flex items-center justify-center">
                    <Users className="h-4 w-4 text-green-500" />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {metrics.contact_adds}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Contacts added to devices
                </p>
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-purple-400 shadow-sm hover:shadow transition-shadow">
              <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                  <CardTitle className="text-sm font-medium text-muted-foreground">VCF DOWNLOADS</CardTitle>
                  <div className="w-8 h-8 bg-purple-50 rounded-full flex items-center justify-center">
                    <Download className="h-4 w-4 text-purple-500" />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {metrics.vcf_downloads}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  VCF files downloaded
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Analytics Chart */}
          {metrics.scan_history.length > 0 ? (
            <Card className="shadow-sm">
              <CardHeader>
                <CardTitle className="text-lg">Scan Activity Trends</CardTitle>
                <CardDescription>
                  VCard scan activity over the selected time period
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6">
                <div className="h-[350px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={metrics.scan_history}>
                      <defs>
                        <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.8}/>
                          <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.1}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-muted" />
                      <XAxis 
                        dataKey="date" 
                        className="text-xs text-muted-foreground"
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(value) => format(new Date(value), 'MMM dd')}
                        padding={{ left: 20, right: 20 }}
                      />
                      <YAxis 
                        className="text-xs text-muted-foreground" 
                        tickLine={false} 
                        axisLine={false}
                        width={30}
                      />
                      <Tooltip 
                        contentStyle={{
                          backgroundColor: 'hsl(var(--background))',
                          borderColor: 'hsl(var(--border))',
                          borderRadius: '8px',
                          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)'
                        }}
                        formatter={(value, name) => [value, 'Scans']}
                        labelFormatter={(label) => format(new Date(label), 'MMMM dd, yyyy')}
                      />
                      <Area 
                        type="monotone" 
                        dataKey="count" 
                        stroke="hsl(var(--primary))" 
                        fillOpacity={1}
                        fill="url(#colorCount)"
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="bg-muted/40 border-dashed">
              <CardContent className="p-6">
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <TrendingUp className="h-12 w-12 text-muted-foreground mb-4" />
                  <h3 className="text-lg font-medium mb-2">No Trend Data Available</h3>
                  <p className="text-sm text-muted-foreground max-w-md">
                    Once your QR code starts getting scanned, you'll see data trends here.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="activity" className="space-y-4">
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Recent Scan Activity
                <Badge variant="outline" className="ml-2">
                  {metrics.recent_scans.length} events
                </Badge>
              </CardTitle>
              <CardDescription>
                Detailed record of all scans and interactions with your VCard
              </CardDescription>
            </CardHeader>
            
            {metrics.recent_scans.length === 0 ? (
              <CardContent className="p-6">
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mb-4">
                    <QrCode className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <h3 className="text-lg font-medium mb-2">No Recent Activity</h3>
                  <p className="text-sm text-muted-foreground max-w-md">
                    When someone scans your QR code or interacts with your digital business card, it will appear here.
                  </p>
                </div>
              </CardContent>
            ) : (
              <CardContent className="p-0">
                <ScrollArea className="h-[500px] rounded-md">
                  <div className="p-4">
                    {metrics.recent_scans.map((scan, index) => (
                      <div 
                        key={index} 
                        className={`flex items-start p-4 rounded-lg mb-3 border border-border hover:bg-muted/30 transition-colors ${
                          scan.action_type === 'scan' ? 'border-l-4 border-l-primary' :
                          scan.action_type === 'contact_add' ? 'border-l-4 border-l-green-400' :
                          scan.action_type === 'vcf_download' ? 'border-l-4 border-l-purple-400' :
                          'border-l-4 border-l-blue-400'
                        }`}
                      >
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                          scan.action_type === 'scan' ? 'bg-primary/10' :
                          scan.action_type === 'contact_add' ? 'bg-green-50' :
                          scan.action_type === 'vcf_download' ? 'bg-purple-50' :
                          'bg-blue-50'
                        }`}>
                          {scan.device_info?.is_mobile ? (
                            <Smartphone className={`w-5 h-5 ${
                              scan.action_type === 'scan' ? 'text-primary' :
                              scan.action_type === 'contact_add' ? 'text-green-500' :
                              scan.action_type === 'vcf_download' ? 'text-purple-500' :
                              'text-blue-500'
                            }`} />
                          ) : (
                            <Globe className={`w-5 h-5 ${
                              scan.action_type === 'scan' ? 'text-primary' :
                              scan.action_type === 'contact_add' ? 'text-green-500' :
                              scan.action_type === 'vcf_download' ? 'text-purple-500' :
                              'text-blue-500'
                            }`} />
                          )}
                        </div>
                        
                        <div className="ml-4 flex-grow min-w-0">
                          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center">
                            <div className="mb-1 sm:mb-0">
                              <div className="flex items-center">
                                <span className="font-medium text-sm">
                                  {scan.action_type === 'scan' ? 'QR Code Scanned' : 
                                  scan.action_type === 'contact_add' ? 'Contact Added' : 
                                  scan.action_type === 'vcf_download' ? 'VCF Downloaded' : 
                                  'Card Viewed'}
                                </span>
                                {scan.device_info?.is_mobile && (
                                  <Badge variant="outline" className="ml-2 text-xs">Mobile</Badge>
                                )}
                              </div>
                              <p className="text-xs text-muted-foreground truncate max-w-xs">
                                {scan.device_info?.browser} on {scan.device_info?.os}
                              </p>
                            </div>
                            
                            <div className="flex items-center gap-1 text-xs text-muted-foreground">
                              <Calendar className="h-3 w-3" />
                              <span>{format(new Date(scan.timestamp), 'MMM dd, yyyy')}</span>
                              <span className="mx-1">•</span>
                              <Clock className="h-3 w-3" />
                              <span>{format(new Date(scan.timestamp), 'h:mm a')}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            )}
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
} 