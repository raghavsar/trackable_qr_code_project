"use client"

import { useState, useCallback, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { 
  XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, AreaChart, Area, Legend 
} from "recharts"
import { 
  QrCode, Smartphone, Loader2, RefreshCw, ArrowLeft,
  Users, Download, Calendar, Clock, TrendingUp, ExternalLink 
} from "lucide-react"
import { useAnalyticsSSE } from '@/hooks/useAnalyticsSSE';
import { useHistoricalAnalytics } from '@/hooks/useHistoricalAnalytics';
import { format, subDays } from 'date-fns';
import { Button } from "@/components/ui/button";
import { useNavigate } from 'react-router-dom'
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";

export default function AnalyticsDashboard() {
  const [timeRange, setTimeRange] = useState('30');
  const [activeTab, setActiveTab] = useState("overview");
  const [showDebug, setShowDebug] = useState(false);
  const [debugInfo, setDebugInfo] = useState<{ apiUrl: string, token: string }>({
    apiUrl: '',
    token: ''
  });
  
  const endDate = format(new Date(), 'yyyy-MM-dd');
  const startDate = format(subDays(new Date(), parseInt(timeRange)), 'yyyy-MM-dd');
  
  // Get real-time metrics with SSE
  const { metrics: realtimeMetrics, error: realtimeError, isConnected, connectionStatus } = useAnalyticsSSE();
  
  // Get historical data
  const { 
    metrics: historicalMetrics, 
    loading: historyLoading, 
    error: historyError,
    refetch: refetchHistory
  } = useHistoricalAnalytics({
    startDate,
    endDate
  });

  // Debug for SSE connection
  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL || 'API URL not set';
    const token = localStorage.getItem('token') ? 'Token exists' : 'No token found';
    
    setDebugInfo({
      apiUrl,
      token
    });
    
    console.log('Analytics Dashboard - Realtime metrics received:', realtimeMetrics);
    console.log('Analytics Dashboard - Connection status:', isConnected);
    
    if (realtimeMetrics) {
      console.log('Analytics counts:', {
        total_scans: realtimeMetrics.total_scans,
        mobile_scans: realtimeMetrics.mobile_scans,
        contact_adds: realtimeMetrics.contact_adds,
        vcf_downloads: realtimeMetrics.vcf_downloads
      });
      
      // Log the complete metrics object keys and types
      console.log('Analytics metrics keys:', Object.keys(realtimeMetrics));
      console.log('Analytics metrics types:', Object.keys(realtimeMetrics).reduce<Record<string, string>>((acc, key) => {
        // Use type assertion to tell TypeScript we know what we're doing
        const metrics = realtimeMetrics as Record<string, any>;
        acc[key] = typeof metrics[key];
        
        if (Array.isArray(metrics[key])) {
          acc[key] += ' (array)';
          if (metrics[key].length > 0) {
            acc[key] += ` - first item type: ${typeof metrics[key][0]}`;
          }
        }
        return acc;
      }, {}));
    } else {
      console.log('No realtime metrics data available yet');
    }
    
    // Debug historical metrics
    console.log('Historical metrics data:', historicalMetrics);
  }, [realtimeMetrics, isConnected, historicalMetrics]);

  const navigate = useNavigate();

  const handleTimeRangeChange = useCallback((value: string) => {
    setTimeRange(value);
  }, []);

  const handleRefresh = useCallback(() => {
    refetchHistory();
    // Force reconnect SSE?
    window.location.reload();
  }, [refetchHistory]);

  const handleBack = () => {
    navigate('/');
  }

  // Format date for IST display
  const formatDate = (dateString: string) => {
    try {
      // Create a date object from the timestamp
      const date = new Date(dateString);
      
      // Format in IST (UTC+5:30)
      // First convert to UTC string, then apply IST offset manually
      const istDate = new Date(date.getTime() + (5.5 * 60 * 60 * 1000));
      return format(istDate, 'MMM dd, yyyy, h:mm a').replace(/\bam\b/g, 'AM').replace(/\bpm\b/g, 'PM') + ' IST';
    } catch (e) {
      return dateString;
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
  );

  // Add this new debug toggle function
  const toggleDebug = useCallback(() => {
    setShowDebug(prev => !prev);
  }, []);

  // After the connection status renderer function, add this debug panel renderer:
  const renderDebugPanel = () => {
    if (!showDebug) return null;
    
    return (
      <div className="fixed bottom-4 right-4 z-50 bg-black/90 text-white p-4 rounded-lg shadow-lg max-w-lg max-h-[80vh] overflow-auto">
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-medium">Debug Information</h3>
          <button onClick={toggleDebug} className="text-xs bg-red-500 px-2 py-1 rounded">Close</button>
        </div>
        <div className="text-xs font-mono space-y-2">
          <div>
            <div className="text-green-400">API URL:</div>
            <div>{debugInfo.apiUrl}</div>
          </div>
          <div>
            <div className="text-green-400">Auth Token:</div>
            <div>{debugInfo.token}</div>
          </div>
          <div>
            <div className="text-green-400">Connection Status:</div>
            <div>{JSON.stringify(connectionStatus, null, 2)}</div>
          </div>
          <div>
            <div className="text-green-400">Realtime Metrics:</div>
            <pre>{JSON.stringify(realtimeMetrics, null, 2)}</pre>
          </div>
          <div>
            <div className="text-green-400">Raw SSE data inspection:</div>
            <button 
              onClick={() => {
                fetch(`${debugInfo.apiUrl}/api/v1/analytics/debug`, {
                  headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                  }
                })
                .then(r => r.json())
                .then(data => console.log('Debug info:', data))
                .catch(err => console.error('Debug fetch error:', err));
              }}
              className="text-xs bg-blue-500 px-2 py-1 rounded mr-2"
            >
              Fetch debug
            </button>
            <button 
              onClick={() => {
                fetch(`${debugInfo.apiUrl}/test/broadcast`, {
                  method: 'POST',
                  headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                  }
                })
                .then(r => r.json())
                .then(data => console.log('Broadcast triggered:', data))
                .catch(err => console.error('Broadcast error:', err));
              }}
              className="text-xs bg-purple-500 px-2 py-1 rounded"
            >
              Test broadcast
            </button>
          </div>
        </div>
      </div>
    );
  };

  // Loading state
  if (historyLoading && !realtimeMetrics) {
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
    );
  }

  // Error state
  if ((realtimeError || historyError) && !realtimeMetrics) {
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
                <p className="text-red-600 mb-4">{realtimeError?.message || historyError?.message || 'An error occurred'}</p>
                <div className="space-y-3">
                  <div className="text-xs text-red-600 bg-red-50 p-2 rounded text-left">
                    <p>API URL: {debugInfo.apiUrl}</p>
                    <p>Auth: {debugInfo.token}</p>
                  </div>
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
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Calculate mobile scans count
  const mobileScansCount = realtimeMetrics?.mobile_scans || 0;

  return (
    <div className="container mx-auto p-4 space-y-6 max-w-7xl">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="flex items-center gap-4">
          <Button onClick={handleBack} variant="ghost" size="icon" className="rounded-full">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Analytics Dashboard</h1>
            <p className="text-muted-foreground text-sm">Track performance and engagement across all your QR codes</p>
          </div>
        </div>
        
        <div className="flex flex-col sm:flex-row items-center gap-2 w-full sm:w-auto">
          {renderConnectionStatus()}
          <div className="flex gap-2 w-full sm:w-auto mt-2 sm:mt-0">
            <Select 
              value={timeRange} 
              onValueChange={handleTimeRangeChange}
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
              disabled={historyLoading}
              className="flex-shrink-0"
              title="Refresh data"
            >
              <RefreshCw className={`h-4 w-4 ${historyLoading ? 'animate-spin' : ''}`} />
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
          {/* Display metrics data as JSON if debug needed */}
          {/* <div className="bg-gray-100 p-4 rounded text-xs overflow-auto max-h-40">
            <pre>{JSON.stringify(realtimeMetrics, null, 2)}</pre>
          </div> */}
          
          {/* Metrics Cards */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  TOTAL SCANS
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-baseline justify-between">
                  <div className="text-3xl font-bold">
                    {realtimeMetrics?.total_scans ?? 0}
                  </div>
                  <div className="p-1.5 rounded-full bg-muted">
                    <QrCode className="h-5 w-5" />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  QR code scans
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  MOBILE SCANS
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-baseline justify-between">
                  <div className="text-3xl font-bold">
                    {realtimeMetrics?.mobile_scans ?? 0}
                  </div>
                  <div className="p-1.5 rounded-full bg-muted">
                    <Smartphone className="h-5 w-5" />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  From mobile devices
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  CONTACT ADDS
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-baseline justify-between">
                  <div className="text-3xl font-bold">
                    {realtimeMetrics?.contact_adds ?? 0}
                  </div>
                  <div className="p-1.5 rounded-full bg-muted">
                    <Users className="h-5 w-5" />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Contacts added to devices
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  VCF DOWNLOADS
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-baseline justify-between">
                  <div className="text-3xl font-bold">
                    {realtimeMetrics?.vcf_downloads ?? 0}
                  </div>
                  <div className="p-1.5 rounded-full bg-muted">
                    <Download className="h-5 w-5" />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  VCF files downloaded
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Analytics Chart */}
          {historicalMetrics.length > 0 ? (
            <Card className="shadow-sm">
              <CardHeader>
                <CardTitle className="text-lg">Scan Activity Trends</CardTitle>
                <CardDescription>
                  QR code scan activity over the selected time period
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6">
                <div className="h-[350px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={historicalMetrics}>
                      <defs>
                        <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.8}/>
                          <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.1}/>
                        </linearGradient>
                        <linearGradient id="colorMobile" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.9}/>
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.2}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-muted" />
                      <XAxis 
                        dataKey="date" 
                        className="text-xs text-muted-foreground"
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(value) => {
                          const date = new Date(value);
                          const istDate = new Date(date.getTime() + (5.5 * 60 * 60 * 1000));
                          return format(istDate, 'MMM dd');
                        }}
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
                        formatter={(value, name) => {
                          const label = name === 'total_scans' ? 'Total Scans' : 'Mobile Scans';
                          return [value, label];
                        }}
                        labelFormatter={(label) => {
                          const date = new Date(label);
                          const istDate = new Date(date.getTime() + (5.5 * 60 * 60 * 1000));
                          return format(istDate, 'MMMM dd, yyyy') + ' (IST)';
                        }}
                      />
                      <Legend 
                        verticalAlign="top" 
                        height={36} 
                        formatter={(value) => {
                          return value === 'total_scans' ? 'Total Scans' : 'Mobile Scans';
                        }}
                      />
                      <Area 
                        type="monotone" 
                        dataKey="total_scans" 
                        stroke="hsl(var(--primary))" 
                        fillOpacity={1}
                        fill="url(#colorTotal)"
                        strokeWidth={2}
                        name="total_scans"
                      />
                      <Area 
                        type="monotone" 
                        dataKey="mobile_scans" 
                        stroke="#3b82f6" 
                        fillOpacity={0.6}
                        fill="url(#colorMobile)"
                        strokeWidth={3}
                        name="mobile_scans"
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
                    Once your QR codes start getting scanned, you'll see data trends here.
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
                  {realtimeMetrics?.recent_scans?.length || 0} events
                </Badge>
              </CardTitle>
              <CardDescription>
                Detailed record of all scans and interactions with your QR codes
              </CardDescription>
            </CardHeader>
            
            {!realtimeMetrics?.recent_scans?.length ? (
              <CardContent className="p-6">
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mb-4">
                    <QrCode className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <h3 className="text-lg font-medium mb-2">No Recent Activity</h3>
                  <p className="text-sm text-muted-foreground max-w-md">
                    When someone scans your QR codes or interacts with your digital business cards, it will appear here.
                  </p>
                </div>
              </CardContent>
            ) : (
              <CardContent className="p-0">
                <ScrollArea className="h-[500px] rounded-md">
                  <div className="p-4">
                    {realtimeMetrics?.recent_scans?.map((scan, index) => (
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
                            <QrCode className={`w-5 h-5 ${
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
                                {scan.vcard_id ? `VCard: ${scan.vcard_id}` : 'System-wide scan'}
                              </p>
                            </div>
                            
                            <div className="flex items-center gap-1 text-xs text-muted-foreground">
                              <Calendar className="h-3 w-3 mr-1" />
                              <span className="bg-muted/50 px-2 py-1 rounded-md">
                                {formatDate(scan.timestamp)}
                              </span>
                            </div>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            {scan.device_info?.browser || 'Unknown browser'} on {scan.device_info?.os || 'Unknown OS'}
                          </p>
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

      {/* Add before the final closing div */}
      {renderDebugPanel()}
      
      {/* Debug toggle button */}
      <button 
        onClick={toggleDebug}
        className="fixed bottom-4 left-4 bg-gray-800 text-white p-2 rounded-full shadow-lg opacity-70 hover:opacity-100 z-50"
        title="Toggle debug panel"
      >
        <span className="sr-only">Debug</span>
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>
    </div>
  );
}