"use client"

import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { AnalyticsService, qrService } from '@/services/api'
import type { AnalyticsData, DailyMetric } from '@/types/analytics'
import type { VCardResponse } from '@/types/api'
import { format, subDays, addDays } from 'date-fns'
import { 
  Loader2, RefreshCw, Smartphone, Globe, ArrowLeft, 
  QrCode, Users, Download, Calendar, Clock, 
  TrendingUp, ExternalLink
} from 'lucide-react'
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  Legend
} from 'recharts'
import { useAnalyticsSSE } from '@/hooks/useAnalyticsSSE'
import { useHistoricalAnalytics } from '@/hooks/useHistoricalAnalytics'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import React from 'react'

const analyticsService = new AnalyticsService()

export default function VCardAnalytics() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [timeRange, setTimeRange] = useState('30')
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState("overview")
  const [vcardInfo, setVcardInfo] = useState<VCardResponse | null>(null)
  const [vcardLoading, setVcardLoading] = useState(true)
  
  // Get real-time updates with VCard ID
  const { metrics: realtimeMetrics, isConnected } = useAnalyticsSSE({ vcardId: id })

  // Get historical data with useHistoricalAnalytics
  const endDate = format(new Date(), 'yyyy-MM-dd');
  const startDate = format(subDays(new Date(), parseInt(timeRange)), 'yyyy-MM-dd');
  
  const { 
    metrics: historicalMetrics, 
    loading: historyLoading, 
    error: historyError,
    refetch: refetchHistory
  } = useHistoricalAnalytics({
    startDate,
    endDate,
    vcardId: id
  });

  // Initialize metrics with default values
  const metrics = {
    total_scans: realtimeMetrics?.total_scans ?? analytics?.total_scans ?? 0,
    mobile_scans: realtimeMetrics?.mobile_scans ?? analytics?.mobile_scans ?? 0,
    contact_adds: realtimeMetrics?.contact_adds ?? analytics?.contact_adds ?? 0,
    vcf_downloads: realtimeMetrics?.vcf_downloads ?? analytics?.vcf_downloads ?? 0,
    recent_scans: realtimeMetrics?.recent_scans ?? analytics?.recent_scans ?? [],
    scan_history: analytics?.scan_history ?? []
  }

  // Process historical metrics to include mobile scans for this VCard
  const processedHistoricalMetrics = historicalMetrics.map(metric => {
    // Filter the data to only include entries for this VCard
    // This assumes the backend API is filtering by VCard ID when used with the specific vcard_id parameter
    return {
      ...metric,
      // Don't use || operator which treats 0 as falsy
      total_scans: metric.total_scans !== undefined ? metric.total_scans : 0,
      mobile_scans: metric.mobile_scans !== undefined ? metric.mobile_scans : 0
    };
  });

  // Generate mock data based on current metrics values - ONLY for development/fallback
  const getMockData = useCallback(() => {
    const mockData = [];
    const today = new Date();
    // Don't use fallback minimum value - use actual metrics
    const metricsTotal = metrics.total_scans;
    const metricsMobile = metrics.mobile_scans;
    
    // If no scans, return empty array
    if (metricsTotal === 0) {
      return [];
    }
    
    // Create a single data point for today
    mockData.push({
      date: format(today, 'yyyy-MM-dd'),
      total_scans: metricsTotal,
      mobile_scans: metricsMobile,
      desktop_scans: metricsTotal - metricsMobile,
      contact_adds: 0,
      vcf_downloads: 0
    });
    
    console.log('Generated simplified mock data with actual values:', mockData);
    return mockData;
  }, [metrics.total_scans, metrics.mobile_scans]);

  // Improved chart data processing that's more robust and eliminates unnecessary re-renders
  const chartData = React.useMemo(() => {
    // First, generate a complete date range for the selected time period
    // This ensures we have entries for every day in the range, even if there were no scans
    const endDate = new Date();
    const startDate = subDays(endDate, parseInt(timeRange));
    const dateRange: string[] = [];
    
    let currentDate = startDate;
    while (currentDate <= endDate) {
      dateRange.push(format(currentDate, 'yyyy-MM-dd'));
      currentDate = addDays(currentDate, 1);
    }
    
    // Create a map with all dates initialized to zero
    const dataMap: Record<string, {
      date: string;
      total_scans: number;
      mobile_scans: number;
      desktop_scans: number;
    }> = {};
    
    // Initialize all dates with zero values
    dateRange.forEach(date => {
      dataMap[date] = {
        date,
        total_scans: 0,
        mobile_scans: 0,
        desktop_scans: 0
      };
    });
    
    // Merge historical metrics data (primary source of truth)
    processedHistoricalMetrics.forEach(metric => {
      // Only include metrics that fall within our date range
      if (dataMap[metric.date]) {
        dataMap[metric.date] = {
          date: metric.date,
          total_scans: metric.total_scans || 0,
          mobile_scans: metric.mobile_scans || 0,
          desktop_scans: (metric.total_scans || 0) - (metric.mobile_scans || 0)
        };
      }
    });
    
    // If we don't have historical metrics but have recent_scans, 
    // process the recent scans by their actual dates
    if (processedHistoricalMetrics.length === 0 && metrics.recent_scans.length > 0) {
      // Group scans by date
      const scansByDate: Record<string, { total: number, mobile: number }> = {};
      
      metrics.recent_scans.forEach(scan => {
        // Only count scan events
        if (scan.action_type === 'scan') {
          const scanDate = format(new Date(scan.timestamp), 'yyyy-MM-dd');
          
          // Initialize if not exists
          if (!scansByDate[scanDate]) {
            scansByDate[scanDate] = { total: 0, mobile: 0 };
          }
          
          // Count the scan
          scansByDate[scanDate].total += 1;
          if (scan.device_info?.is_mobile) {
            scansByDate[scanDate].mobile += 1;
          }
        }
      });
      
      // Update the data map with the processed scans by date
      Object.entries(scansByDate).forEach(([date, counts]) => {
        // Only update if the date is within our range
        if (dataMap[date]) {
          dataMap[date] = {
            date,
            total_scans: counts.total,
            mobile_scans: counts.mobile,
            desktop_scans: counts.total - counts.mobile
          };
        }
      });
    }
    
    // For the current day, we might need to supplement with real-time data
    // as the historical metrics might not have the latest scans
    const today = format(new Date(), 'yyyy-MM-dd');
    
    // Count today's scans from real-time data
    let todayTotalFromRecentScans = 0;
    let todayMobileFromRecentScans = 0;
    
    // Process recent scans for today only
    metrics.recent_scans.forEach(scan => {
      const scanDate = format(new Date(scan.timestamp), 'yyyy-MM-dd');
      
      // Only count actual scan events for today
      if (scan.action_type === 'scan' && scanDate === today) {
        todayTotalFromRecentScans++;
        if (scan.device_info?.is_mobile) {
          todayMobileFromRecentScans++;
        }
      }
    });
    
    // If we have more recent scans than what's in historical data for today,
    // update today's values (this handles real-time updates better)
    if (todayTotalFromRecentScans > (dataMap[today]?.total_scans || 0)) {
      dataMap[today] = {
        date: today,
        total_scans: todayTotalFromRecentScans,
        mobile_scans: todayMobileFromRecentScans,
        desktop_scans: todayTotalFromRecentScans - todayMobileFromRecentScans
      };
    }
    
    // Only as a last resort fallback:
    // If we have no data points at all (no historical data and no processed recent_scans),
    // but we do have total metrics, then show as single data point for today
    const hasAnyDataPoints = Object.values(dataMap).some(d => d.total_scans > 0);
    if (!hasAnyDataPoints && metrics.total_scans > 0) {
      console.log('No historical or processed scan data available, falling back to showing all scans for today');
      dataMap[today] = {
        date: today,
        total_scans: metrics.total_scans,
        mobile_scans: metrics.mobile_scans,
        desktop_scans: metrics.total_scans - metrics.mobile_scans
      };
    }
    
    // Convert to an array and sort by date
    const dataArray = Object.values(dataMap).sort((a, b) => 
      new Date(a.date).getTime() - new Date(b.date).getTime()
    );
    
    console.log('Generated chart data with complete date range:', {
      timeRange,
      datesInRange: dateRange.length,
      dataPointsGenerated: dataArray.length,
      hasData: dataArray.some(d => d.total_scans > 0),
      datesWithData: dataArray.filter(d => d.total_scans > 0).map(d => d.date)
    });
    
    return dataArray;
  }, [timeRange, processedHistoricalMetrics, metrics.total_scans, metrics.mobile_scans, metrics.recent_scans]);
  
  // Refresh historical data when real-time metrics change
  useEffect(() => {
    if (realtimeMetrics?.total_scans !== undefined) {
      // Only refresh if there's a meaningful change in scan count
      if (realtimeMetrics.total_scans > metrics.total_scans) {
        console.log('Real-time metrics increased, refreshing historical data', {
          'realtimeMetrics.total_scans': realtimeMetrics.total_scans,
          'previous total_scans': metrics.total_scans
        });
        
        // Use a short delay to ensure backend has processed the latest data
        const timer = setTimeout(() => {
          refetchHistory();
        }, 1500);
        
        return () => clearTimeout(timer);
      }
    }
  }, [realtimeMetrics?.total_scans, metrics.total_scans, refetchHistory]);

  useEffect(() => {
    fetchAnalytics()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, timeRange])

  // Separate useEffect for fetching VCard info - only need to fetch once per ID
  useEffect(() => {
    fetchVcardInfo()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const fetchAnalytics = async () => {
    if (!id) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const data = await analyticsService.getVCardAnalytics(id, timeRange);
      setAnalytics(data);
    } catch (err: any) {
      console.error('Failed to fetch analytics data:', err);
      setError(err.message || 'Failed to fetch analytics data');
    } finally {
      setLoading(false);
    }
  };

  const fetchVcardInfo = async () => {
    if (!id) return;
    
    try {
      setVcardLoading(true);
      const vcardData = await qrService.getVCard(id);
      setVcardInfo(vcardData);
    } catch (err) {
      console.error("Error fetching VCard information:", err);
      // We don't set an error state here as the analytics is the primary functionality
    } finally {
      setVcardLoading(false);
    }
  };

  const handleBack = () => {
    navigate('/analytics')
  }

  const handleRefresh = useCallback(() => {
    // Refresh all data
    fetchAnalytics();
    refetchHistory();
    fetchVcardInfo(); // Also refresh VCard info
  }, [fetchAnalytics, refetchHistory, fetchVcardInfo]);

  // Format date for display
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
  const renderConnectionStatus = () => {
    // Check if we have actual data loaded, not just an empty metrics object
    const hasRealData = metrics.total_scans > 0 || metrics.recent_scans.length > 0;
    // Check if we've completed loading (even if there's no data)
    const loadingComplete = !loading && !historyLoading && !vcardLoading;
    // Consider the connection as fully loaded if we're connected AND either:
    // 1. We have actual data (non-zero metrics)
    // 2. We have confirmed data has been loaded (even if all zeros)
    // 3. All loading processes have completed
    const isDataLoaded = isConnected && (hasRealData || (realtimeMetrics !== undefined && analytics !== null) || loadingComplete);
    
    return (
      <Badge variant={isDataLoaded ? "success" : "outline"} className="gap-1.5 ml-2">
        <div className={`w-2 h-2 rounded-full ${
          isDataLoaded ? 'bg-green-500' : 'bg-blue-500'
        }`} />
        <span>{isDataLoaded ? 'Connected' : 'Healthy'}</span>
      </Badge>
    );
  }

  // Loading state
  if ((loading || historyLoading) && !metrics.total_scans && !metrics.recent_scans.length && !processedHistoricalMetrics.length && !chartData.length) {
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
  if ((error || historyError) && !metrics.total_scans && !metrics.recent_scans.length && !processedHistoricalMetrics.length && !chartData.length) {
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
                <p className="text-red-600 mb-4">{error || historyError?.message || 'An error occurred'}</p>
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
            <h1 className="text-2xl font-bold">
              {vcardLoading 
                ? "VCard Analytics" 
                : vcardInfo 
                  ? `${vcardInfo.first_name} ${vcardInfo.last_name} VCard's Analytics` 
                  : "VCard Analytics"}
            </h1>
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
              disabled={loading || historyLoading}
              className="flex-shrink-0"
              title="Refresh data"
            >
              <RefreshCw className={`h-4 w-4 ${loading || historyLoading ? 'animate-spin' : ''}`} />
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
                  {metrics.mobile_scans}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  From mobile devices
                </p>
                {/* Mobile percentage indicator */}
                {metrics.total_scans > 0 && (
                  <div className="mt-2">
                    <div className="w-full bg-gray-200 rounded-full h-1.5">
                      <div 
                        className="bg-blue-500 h-1.5 rounded-full" 
                        style={{width: `${Math.min(100, (metrics.mobile_scans / metrics.total_scans) * 100)}%`}}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {metrics.total_scans > 0 
                        ? `${Math.round((metrics.mobile_scans / metrics.total_scans) * 100)}% of total scans` 
                        : 'No data yet'}
                    </p>
                  </div>
                )}
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

          {/* Analytics Chart - Always show this */}
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">Scan Activity Trends</CardTitle>
              <CardDescription>
                QR code scan activity over the selected time period
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <div className="h-[350px]">
                {chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart 
                      data={chartData}
                      margin={{ top: 20, right: 20, left: 0, bottom: 0 }}
                      key={`vcard-analytics-chart-${id}-${timeRange}`}
                    >
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
                        allowDecimals={false}
                        domain={[0, 'auto']}
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
                ) : (
                  <div className="flex flex-col items-center justify-center h-full">
                    <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mb-4">
                      <TrendingUp className="h-8 w-8 text-muted-foreground" />
                    </div>
                    <h3 className="text-lg font-medium mb-2">No Scan Activity</h3>
                    <p className="text-sm text-muted-foreground max-w-md text-center">
                      When your QR code is scanned, activity will appear here. Check back after sharing your VCard.
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
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
                              <Calendar className="h-3 w-3 mr-1" />
                              <span className="bg-muted/50 px-2 py-1 rounded-md">
                                {formatDate(scan.timestamp)}
                              </span>
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