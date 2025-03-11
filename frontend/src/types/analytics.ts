export interface ScanEvent {
  vcard_id: string
  timestamp: string
  device_info: {
    is_mobile: boolean
    device: string
    os: string
    browser: string
  }
  action_type: 'scan' | 'contact_add' | 'vcf_download' | 'page_view'
}

export interface InteractionBreakdown {
  direct_scans: number
  vcf_downloads: number
  contact_adds: number
}

export interface AnalyticsMetrics {
  total_scans: number
  contact_adds: number
  vcf_downloads: number
  mobile_scans: number
  desktop_scans: number
  recent_scans: ScanEvent[]
  recent_total?: number
  recent_contact_adds?: number
  recent_vcf_downloads?: number
  timestamp?: string
  vcard_id?: string
  interaction_breakdown?: InteractionBreakdown
  hourly_distribution?: Record<string, number>
  daily_distribution?: Record<string, number>
}

export interface HistoricalMetrics {
  total_scans: number;
  contact_adds: number;
  vcf_downloads: number;
  mobile_scans: number;
  desktop_scans: number;
}

export interface DailyMetric {
  date: string
  total_scans: number
  contact_adds: number
  vcf_downloads: number
  mobile_scans: number
  desktop_scans: number
}

export interface ScanHistoryEntry {
  date: string;
  count: number;
  action: string;
}

export interface AnalyticsData {
  qr_id: string;
  vcard_id?: string;
  timeRange: string;
  total_scans: number;
  contact_adds: number;
  vcf_downloads: number;
  mobile_scans: number;
  desktop_scans: number;
  scan_history: ScanHistoryEntry[];
  recent_scans: ScanEvent[];
  interaction_breakdown?: InteractionBreakdown;
  hourly_distribution?: Record<string, number>;
  daily_distribution?: Record<string, number>;
  timestamp?: string;
}

export interface ScanEntry {
  vcard_id: string;
  timestamp: string;
  device_info: {
    is_mobile: boolean;
    browser: string;
    os: string;
  };
  action_type: 'scan' | 'contact_add' | 'vcf_download' | 'page_view';
} 