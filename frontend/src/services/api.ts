import type { QRCodeResponse, VCardData, LandingPageData, ShortLinkData, VCardResponse, QRTemplate, QRDesignOptions, AnalyticsResponse } from '@/types/api'
import type { AnalyticsData } from '@/types/analytics'
import { axiosInstance } from './axios'
import axios, { AxiosInstance } from 'axios'
import type { QRGenerateRequest } from '../types/api'

const API_URL = import.meta.env.VITE_API_URL;
const API_VERSION = 'v1';

export const getApiUrl = (path: string): string => {
  return `${API_URL}/api/${API_VERSION}${path}`;
};

export class QRService {
  private api: AxiosInstance;

  constructor(api: AxiosInstance) {
    this.api = api;
  }

  private getHeaders() {
    const token = localStorage.getItem('token')
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    }
  }

  async createVCard(data: VCardData): Promise<VCardResponse> {
    const response = await this.api.post('/vcards', data);
    const vcard = response.data;
    // Ensure we have a valid ID
    if (!vcard.id && vcard._id) {
      vcard.id = vcard._id;
    }
    return vcard;
  }

  async generateQRCode(data: QRGenerateRequest): Promise<QRCodeResponse> {
    // Ensure vcard_id is provided
    if (!data.vcard_id) {
      throw new Error('vcard_id is required');
    }
    const response = await this.api.post('/qrcodes', data);
    return response.data;
  }

  async listQRCodes(): Promise<QRCodeResponse[]> {
    const response = await this.api.get('/qrcodes');
    return response.data;
  }

  async deleteQRCode(id: string): Promise<void> {
    await this.api.delete(`/qrcodes/${id}`);
  }

  async getQRCode(id: string): Promise<QRCodeResponse> {
    const response = await this.api.get(`/qrcodes/${id}`);
    return response.data;
  }

  async updateQRCode(id: string, data: QRGenerateRequest): Promise<QRCodeResponse> {
    const response = await this.api.put(`/qrcodes/${id}`, data);
    return response.data;
  }

  async getAnalytics(trackingId: string): Promise<AnalyticsResponse> {
    const response = await axiosInstance.get(`/analytics/${trackingId}`)
    return response.data
  }

  async getVCard(vcardId: string): Promise<VCardData> {
    try {
      console.log('Getting VCard with ID:', vcardId)
      
      if (!vcardId || typeof vcardId !== 'string') {
        console.error('Invalid VCard ID:', vcardId)
        throw new Error('Invalid VCard ID')
      }

      // Validate VCard ID format (MongoDB ObjectId is 24 hex characters)
      if (!/^[0-9a-fA-F]{24}$/.test(vcardId)) {
        console.error('Invalid VCard ID format:', vcardId)
        throw new Error('Invalid VCard ID format')
      }

      console.log('Making request to get VCard:', vcardId)
      const response = await axiosInstance.get(`/vcards/${vcardId}`)
      const vcard = response.data
      
      console.log('Received VCard data:', vcard)
      
      if (!vcard || !vcard._id) {
        console.error('Invalid VCard data received from server:', vcard)
        throw new Error('Invalid VCard data received from server')
      }

      // Ensure we have all required fields
      if (!vcard.first_name || !vcard.last_name || !vcard.email) {
        console.error('Missing required fields in VCard data:', vcard)
        throw new Error('Invalid VCard data: missing required fields')
      }

      return {
        ...vcard,
        vcard_id: vcard._id // Ensure we set the vcard_id from MongoDB's _id
      }
    } catch (error: any) {
      console.error('Error fetching VCard:', error)
      if (error.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        console.error('Server response error:', error.response.status, error.response.data)
        throw error
      } else if (error.request) {
        // The request was made but no response was received
        console.error('No response received from server')
        throw new Error('No response received from server')
      } else {
        // Something happened in setting up the request that triggered an Error
        console.error('Request setup error:', error.message)
        throw error
      }
    }
  }

  async updateQRCodeWithDesign(
    qrId: string,
    data: VCardData & {
      design?: QRDesignOptions;
      template_id?: string;
    }
  ) {
    try {
      const response = await axios.put(
        `${API_URL}/qrcodes/${qrId}`,
        data,
        { headers: this.getHeaders() }
      )
      return response.data
    } catch (error) {
      console.error('Failed to update QR code:', error)
      throw error
    }
  }
}

export const qrService = new QRService(axiosInstance)

export class AnalyticsService {
  async getAnalytics(timeRange: string): Promise<AnalyticsData> {
    const response = await axiosInstance.get(`/analytics/dashboard?timeRange=${timeRange}`)
    return response.data.data
  }

  async getQRCodeAnalytics(qrCodeId: string, timeRange: string): Promise<AnalyticsData> {
    const response = await axiosInstance.get(`/analytics/qr/${qrCodeId}?timeRange=${timeRange}`)
    return response.data.data
  }
}

export const analyticsService = new AnalyticsService()

const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for authentication
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
); 