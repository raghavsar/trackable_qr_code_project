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

  async getVCard(vcardId: string): Promise<VCardResponse> {
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
      const response = await axiosInstance.get(`/vcards/public/${vcardId}`)
      const vcard = response.data
      
      console.log('Received VCard data:', vcard)
      
      if (!vcard || !vcard._id) {
        console.error('Invalid VCard data received from server:', vcard)
        throw new Error('Invalid VCard data received from server')
      }
      // Convert to VCardResponse format
      return {
        id: vcard._id,
        _id: vcard._id,
        first_name: vcard.first_name,
        last_name: vcard.last_name,
        user_id: vcard.user_id, // Add missing required user_id field
        email: vcard.email,
        mobile_number: vcard.mobile_number,
        work_number: vcard.work_number,
        profile_picture: vcard.profile_picture,
        company: vcard.company,
        title: vcard.title,
        website: vcard.website,
        address: vcard.address,
        notes: vcard.notes,
        created_at: vcard.created_at,
        updated_at: vcard.updated_at
      }
    } catch (error) {
      console.error('Error fetching VCard:', error)
      throw error
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
    try {
      console.log('📊 Fetching general analytics with timeRange:', timeRange);
      const response = await axiosInstance.get(`/analytics/metrics?timeRange=${timeRange}`);
      console.log('📊 Analytics response:', response.data);
      return response.data;
    } catch (error) {
      console.error('❌ Error fetching analytics:', error);
      if (axios.isAxiosError(error)) {
        console.error('Response:', error.response?.data);
        console.error('Status:', error.response?.status);
        console.error('Headers:', error.response?.headers);
      }
      throw error;
    }
  }

  async getQRCodeAnalytics(qrCodeId: string, timeRange: string = '30'): Promise<AnalyticsData> {
    try {
      console.log('📊 Fetching VCard analytics:', {
        vcardId: qrCodeId,
        timeRange,
        url: `/analytics/vcard/${qrCodeId}?timeRange=${timeRange}d`
      });

      const token = localStorage.getItem('token');
      console.log('🔑 Auth token present:', !!token);

      const response = await axiosInstance.get(`/analytics/vcard/${qrCodeId}?timeRange=${timeRange}d`);
      console.log('📊 VCard Analytics response:', response.data);
      return response.data;
    } catch (error) {
      console.error('❌ Error fetching VCard analytics:', error);
      if (axios.isAxiosError(error)) {
        console.error('Full error details:', {
          response: error.response?.data,
          status: error.response?.status,
          headers: error.response?.headers
        });
      }
      throw error;
    }
  }

  async getVCardAnalytics(vcardId: string, timeRange: string = '30'): Promise<AnalyticsData> {
    return this.getQRCodeAnalytics(vcardId, timeRange);
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