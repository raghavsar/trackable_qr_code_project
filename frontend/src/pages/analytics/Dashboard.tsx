"use client"

import { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Line, LineChart, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { ChartContainer, ChartTooltipContent } from "@/components/ui/chart"
import { Globe, Smartphone, Loader2, RefreshCw, AlertCircle, ArrowLeft } from "lucide-react"
import { useAnalyticsSSE } from '@/hooks/useAnalyticsSSE';
import { useHistoricalAnalytics } from '@/hooks/useHistoricalAnalytics';
import { format, subDays } from 'date-fns';
import { Button } from "@/components/ui/button";
import { useNavigate } from 'react-router-dom'

export default function AnalyticsDashboard() {
  const [timeRange, setTimeRange] = useState('30');
  const endDate = format(new Date(), 'yyyy-MM-dd');
  const startDate = format(subDays(new Date(), parseInt(timeRange)), 'yyyy-MM-dd');
  
  const { metrics: realtimeMetrics, error: realtimeError, isConnected } = useAnalyticsSSE();
  const { 
    metrics: historicalMetrics, 
    loading: historyLoading, 
    error: historyError,
    hasData,
    refetch: refetchHistory
  } = useHistoricalAnalytics({
    startDate,
    endDate
  });

  const navigate = useNavigate()

  const handleTimeRangeChange = useCallback((value: string) => {
    setTimeRange(value);
  }, []);

  const handleRefresh = useCallback(() => {
    refetchHistory();
  }, [refetchHistory]);

  const handleBack = () => {
    navigate('/')
  }

  const renderError = (message: string) => (
    <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
      <AlertCircle className="h-5 w-5" />
      <span>{message}</span>
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
  );

  const renderEmptyState = () => (
    <div className="h-full flex flex-col items-center justify-center text-muted-foreground space-y-4">
      <div className="text-center">
        <p className="text-lg font-medium mb-2">No Historical Data Available</p>
        <p className="text-sm">Start generating QR codes to see analytics data here.</p>
      </div>
      <Button 
        variant="outline" 
        size="sm" 
        onClick={handleRefresh}
        className="gap-2"
      >
        <RefreshCw className="h-4 w-4" />
        Check Again
      </Button>
    </div>
  );

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
  );

  if (realtimeError || historyError) {
    return (
      <div className="p-8">
        <Button onClick={handleBack} variant="ghost" className="mb-4">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <div className="space-y-4">
          {renderError(realtimeError?.message || historyError?.message || 'An error occurred')}
          <Button onClick={handleRefresh}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  if (historyLoading) {
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
    );
  }

  return (
    <div className="container mx-auto p-4 space-y-6">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={handleBack}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <h1 className="text-2xl font-bold">Analytics Dashboard</h1>
        </div>
        <div className="flex items-center gap-2">
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
          >
            <RefreshCw className={`h-4 w-4 ${historyLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      <div className="flex justify-between items-center">
        <div className="grid grid-cols-3 gap-4">
          <Card>
            <CardHeader className="p-4">
              <CardTitle className="text-sm font-medium text-muted-foreground">TOTAL SCANS</CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="text-2xl font-bold">{realtimeMetrics?.total_scans || 0}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="p-4">
              <CardTitle className="text-sm font-medium text-muted-foreground">CONTACT ADDS</CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="text-2xl font-bold">{realtimeMetrics?.contact_adds || 0}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="p-4">
              <CardTitle className="text-sm font-medium text-muted-foreground">VCF DOWNLOADS</CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="text-2xl font-bold">{realtimeMetrics?.vcf_downloads || 0}</div>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardContent className="p-6">
          <ChartContainer
            className="h-[300px]"
            config={{
              total_scans: {
                label: "Total Scans",
                color: "hsl(var(--primary))",
              },
              mobile_scans: {
                label: "Mobile Scans",
                color: "hsl(var(--secondary))",
              }
            }}
          >
            {historyLoading ? (
              <div className="h-full flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : !hasData ? (
              renderEmptyState()
            ) : historicalMetrics.length === 0 ? (
              <div className="h-full flex items-center justify-center text-muted-foreground">
                No data available for the selected period
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart 
                  data={historicalMetrics} 
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis 
                    dataKey="date" 
                    className="text-sm text-muted-foreground" 
                    tickLine={false} 
                    axisLine={false}
                    tickFormatter={(value) => format(new Date(value), 'MMM dd')}
                  />
                  <YAxis
                    className="text-sm text-muted-foreground"
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip content={<ChartTooltipContent />} />
                  <Line 
                    type="monotone" 
                    dataKey="total_scans" 
                    stroke="hsl(var(--primary))" 
                    strokeWidth={2} 
                    dot={false} 
                  />
                  <Line 
                    type="monotone" 
                    dataKey="mobile_scans" 
                    stroke="hsl(var(--secondary))" 
                    strokeWidth={2} 
                    dot={false} 
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </ChartContainer>
        </CardContent>
      </Card>

      <div className="space-y-4">
        {realtimeMetrics?.recent_scans?.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No recent scans to display
          </div>
        ) : (
          realtimeMetrics?.recent_scans.map((scan, index) => (
            <Card key={index}>
              <CardContent className="p-4 flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-muted rounded-full flex items-center justify-center">
                    {scan.device_info.is_mobile ? (
                      <Smartphone className="w-4 h-4 text-muted-foreground" />
                    ) : (
                      <Globe className="w-4 h-4 text-muted-foreground" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium">
                      {scan.action_type === 'contact_add' ? 'Contact Added' : 'VCF Downloaded'}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {scan.device_info.browser} on {scan.device_info.os}
                    </p>
                  </div>
                </div>
                <div className="text-sm text-muted-foreground">
                  {format(new Date(scan.timestamp), 'MMM dd, yyyy, hh:mm a')}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}