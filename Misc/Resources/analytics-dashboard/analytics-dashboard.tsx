"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Line, LineChart, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Globe } from "lucide-react"

// Sample data for the line chart
const chartData = [
  { date: "15 Dec", scans: 0 },
  { date: "19 Dec", scans: 2 },
  { date: "23 Dec", scans: 0 },
  { date: "27 Dec", scans: 1 },
  { date: "31 Dec", scans: 0 },
  { date: "4 Jan", scans: 1 },
  { date: "8 Jan", scans: 1 },
  { date: "12 Jan", scans: 3 },
]

interface ScanEntry {
  location: string
  device: string
  browser: string
  timestamp: string
}

const recentScans: ScanEntry[] = [
  {
    location: "Oklahoma City, Oklahoma, United States",
    device: "Chrome Mobile",
    browser: "Chrome",
    timestamp: "Jan. 11, 2025, 06:25 p.m.",
  },
  {
    location: "Čáslav, Central Bohemia, Czechia",
    device: "iPhone, Mobile Safari",
    browser: "Safari",
    timestamp: "Jan. 10, 2025, 10:46 a.m.",
  },
]

export default function AnalyticsDashboard() {
  return (
    <div className="container mx-auto p-4 space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex gap-4">
          <Card>
            <CardHeader className="p-4">
              <CardTitle className="text-sm font-medium text-muted-foreground">TOTAL SCANS</CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="text-2xl font-bold">14</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="p-4">
              <CardTitle className="text-sm font-medium text-muted-foreground">UNIQUE SCANS</CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="text-2xl font-bold">14</div>
            </CardContent>
          </Card>
        </div>
        <Select defaultValue="30">
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Select time period" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
            <SelectItem value="90">Last 90 days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent className="p-6">
          <ChartContainer
            className="h-[300px]"
            config={{
              scans: {
                label: "Scans",
                color: "hsl(var(--primary))",
              },
            }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="date" className="text-sm text-muted-foreground" tickLine={false} axisLine={false} />
                <YAxis
                  className="text-sm text-muted-foreground"
                  tickLine={false}
                  axisLine={false}
                  ticks={[0, 1, 2, 3]}
                />
                <Tooltip content={<ChartTooltipContent />} />
                <Line type="monotone" dataKey="scans" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartContainer>
        </CardContent>
      </Card>

      <div className="space-y-4">
        {recentScans.map((scan, index) => (
          <Card key={index}>
            <CardContent className="p-4 flex justify-between items-center">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-muted rounded-full flex items-center justify-center">
                  <Globe className="w-4 h-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-sm font-medium">{scan.location}</p>
                  <p className="text-sm text-muted-foreground">{scan.device}</p>
                </div>
              </div>
              <div className="text-sm text-muted-foreground">{scan.timestamp}</div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

