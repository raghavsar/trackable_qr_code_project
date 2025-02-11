export interface ScanEvent {
  vcard_id: string
  timestamp: string
  device_info: {
    is_mobile: boolean
    device: string
    os: string
    browser: string
  }
  action_type: 'contact_add' | 'vcf_download'
}

export interface AnalyticsMetrics {
  total_scans: number
  contact_adds: number
  vcf_downloads: number
  mobile_scans: number
  desktop_scans: number
  recent_scans: ScanEvent[]
}

export interface HistoricalMetrics {
  total_scans: number;
  contact_adds: number;
  vcf_downloads: number;
  mobile_scans: number;
  desktop_scans: number;
}

export interface DailyMetric {
  date: string;
  total_scans: number;
  contact_adds: number;
  vcf_downloads: number;
  mobile_scans: number;
  desktop_scans: number;
}

export interface ScanEntry {
  vcard_id: string;
  timestamp: string;
  device_info: {
    is_mobile: boolean;
    browser: string;
    os: string;
  };
  action_type: 'contact_add' | 'vcf_download';
} 