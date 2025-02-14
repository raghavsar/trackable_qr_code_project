export interface QRCodeResponse {
  id: string
  tracking_id: string
  qr_image: string
  qr_image_url: string
  created_at: string
  updated_at?: string
  type: string
  total_scans: number
  metadata: {
    vcard_id?: string
    vcard_name?: string
    [key: string]: any
  }
  design?: QRDesignOptions
  template_id?: string
}

export interface AnalyticsResponse {
  total_scans: number
  unique_scans: number
  locations: Record<string, number>
  devices: Record<string, number>
  success: boolean
  data: AnalyticsData
  error?: string
}

export interface AddressData {
  street?: string
  city?: string
  state?: string
  country?: string
  postCode?: string
}

export interface VCardData {
  _id?: string  // MongoDB ID
  vcard_id?: string  // Optional for creation, required for updates
  first_name: string
  last_name: string
  email: string
  mobile_number?: string  // TEL;CELL in v3.0
  work_number?: string    // TEL;WORK in v3.0
  profile_picture?: string  // PHOTO;VALUE=URL or PHOTO;ENCODING=b in v3.0
  company?: string  // ORG in v3.0
  title?: string   // TITLE in v3.0
  website?: string // URL in v3.0
  address?: {
    street?: string
    city?: string
    state?: string
    country?: string
    zip_code?: string
  }
  notes?: string  // NOTE in v3.0
}

export interface LandingPageData {
  title: string
  url: string
  description: string
}

export interface ShortLinkData {
  originalUrl: string
  customAlias?: string
}

export interface VCardResponse {
  id: string;
  _id?: string;  // MongoDB ID
  first_name: string;
  last_name: string;
  email: string;
  mobile_number?: string;  // TEL;CELL in v3.0
  work_number?: string;    // TEL;WORK in v3.0
  profile_picture?: string;  // PHOTO;VALUE=URL or PHOTO;ENCODING=b in v3.0
  company?: string;  // ORG in v3.0
  title?: string;   // TITLE in v3.0
  website?: string; // URL in v3.0
  address?: {
    street?: string;
    city?: string;
    state?: string;
    country?: string;
    zip_code?: string;
  };
  notes?: string;  // NOTE in v3.0
  created_at: string;
  updated_at: string;
}

export interface ScanEntry {
  location: string
  device: string
  browser: string
  timestamp: string
  ip?: string
  country?: string
  city?: string
  region?: string
}

export interface AnalyticsData {
  total_scans: number
  scans_by_date: {
    date: string
    count: number
  }[]
  scans_by_location: {
    country: string
    count: number
  }[]
  scans_by_device: {
    device: string
    count: number
  }[]
}

export interface QRDesignOptions {
  pattern_style?: 'square' | 'rounded' | 'dots' | 'gapped' | 'vertical' | 'horizontal';
  eye_style?: 'square' | 'circle';
  foreground_color?: string;
  background_color?: string;
  logo_url?: string;
  logo_size?: number;
  logo_background?: boolean;
  logo_round?: boolean;
  error_correction?: 'L' | 'M' | 'Q' | 'H';
  box_size?: number;
  border?: number;
}

export interface QRTemplate {
  id?: string;
  name: string;
  description?: string;
  design: QRDesignOptions;
  category: 'vcard' | 'url' | 'text';
  is_public: boolean;
  user_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface QRGenerateRequest {
  vcard_id: string;
  design?: QRDesignOptions;
} 