import type { QRCodeResponse, VCardData, LandingPageData, ShortLinkData, AnalyticsResponse, AnalyticsData, VCardResponse, QRTemplate, QRDesignOptions } from '@/types/api'
import { axiosInstance } from './axios'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL;
const API_VERSION = 'v1';

export const getApiUrl = (path: string): string => {
  return `${API_URL}/api/${API_VERSION}${path}`;
};

class QRService {
  private getHeaders() {
    const token = localStorage.getItem('token')
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    }
  }

  async createVCard(data: VCardData): Promise<VCardResponse> {
    const response = await axiosInstance.post('/vcards', data)
    return response.data
  }

  async generateVCardQR(data: VCardData): Promise<QRCodeResponse> {
    // First create the VCard
    const vcard = await this.createVCard(data)
    
    // Then generate QR code with the VCard ID
    const response = await axiosInstance.post('/qrcodes', { vcard_id: vcard._id })
    return response.data
  }

  async generateLandingPageQR(data: LandingPageData): Promise<QRCodeResponse> {
    const response = await axiosInstance.post('/qrcodes/landing-page', data)
    return response.data
  }

  async generateShortLinkQR(data: ShortLinkData): Promise<QRCodeResponse> {
    const response = await axiosInstance.post('/qrcodes/short-link', data)
    return response.data
  }

  async listQRCodes(): Promise<QRCodeResponse[]> {
    const response = await axiosInstance.get('/qrcodes')
    return response.data
  }

  async deleteQRCode(id: string): Promise<void> {
    await axiosInstance.delete(`/qrcodes/${id}`)
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

  async updateQRCode(qrId: string, data: VCardData): Promise<QRCodeResponse> {
    try {
      // First update the VCard
      if (!data.vcard_id) {
        console.error('VCard ID missing from data:', data)
        throw new Error('VCard ID is required for update')
      }

      // Validate VCard ID format
      if (!/^[0-9a-fA-F]{24}$/.test(data.vcard_id)) {
        console.error('Invalid VCard ID format:', data.vcard_id)
        throw new Error('Invalid VCard ID format')
      }
      
      console.log('Updating VCard with ID:', data.vcard_id)
      const vcardResponse = await axiosInstance.put(`/vcards/${data.vcard_id}`, {
        first_name: data.first_name,
        last_name: data.last_name,
        email: data.email,
        mobile_number: data.mobile_number,
        work_number: data.work_number,
        profile_picture: data.profile_picture,
        company: data.company,
        title: data.title,
        website: data.website,
        notes: data.notes,
        address: data.address
      })
      console.log('VCard update response:', vcardResponse.data)
      
      console.log('VCard updated, now updating QR code with ID:', qrId)
      // Then update QR code
      const response = await axiosInstance.put(`/qrcodes/${qrId}`, {
        vcard_id: data.vcard_id
      })
      
      console.log('QR code update response:', response.data)
      return response.data
    } catch (error: any) {
      console.error('Error updating QR code:', error)
      if (error.response) {
        console.error('Server response error:', error.response.status, error.response.data)
      }
      throw error
    }
  }

  // Template methods
  async createTemplate(template: Omit<QRTemplate, 'id' | 'user_id'>) {
    try {
      const response = await axios.post(
        `${API_URL}/templates`,
        template,
        { headers: this.getHeaders() }
      )
      return response.data
    } catch (error) {
      console.error('Failed to create template:', error)
      throw error
    }
  }

  async listTemplates() {
    try {
      const response = await axios.get(
        `${API_URL}/templates`,
        { headers: this.getHeaders() }
      )
      return response.data
    } catch (error) {
      console.error('Failed to fetch templates:', error)
      throw error
    }
  }

  async getTemplate(templateId: string) {
    try {
      const response = await axios.get(
        `${API_URL}/templates/${templateId}`,
        { headers: this.getHeaders() }
      )
      return response.data
    } catch (error) {
      console.error('Failed to fetch template:', error)
      throw error
    }
  }

  async updateTemplate(templateId: string, template: Omit<QRTemplate, 'id' | 'user_id'>) {
    try {
      const response = await axios.put(
        `${API_URL}/templates/${templateId}`,
        template,
        { headers: this.getHeaders() }
      )
      return response.data
    } catch (error) {
      console.error('Failed to update template:', error)
      throw error
    }
  }

  async deleteTemplate(templateId: string) {
    try {
      const response = await axios.delete(
        `${API_URL}/templates/${templateId}`,
        { headers: this.getHeaders() }
      )
      return response.data
    } catch (error) {
      console.error('Failed to delete template:', error)
      throw error
    }
  }

  // Update QR code with design
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

export const qrService = new QRService()

class AnalyticsService {
  async getAnalytics(timeRange: string): Promise<AnalyticsData> {
    const response = await axiosInstance.get(`/analytics/dashboard?timeRange=${timeRange}`)
    const data = response.data
    if (!data.success) {
      throw new Error(data.error || 'Failed to fetch analytics data')
    }
    return data.data
  }

  async getQRCodeAnalytics(qrCodeId: string, timeRange: string): Promise<AnalyticsData> {
    const response = await axiosInstance.get(`/analytics/qr/${qrCodeId}?timeRange=${timeRange}`)
    const data = response.data
    if (!data.success) {
      throw new Error(data.error || 'Failed to fetch QR code analytics')
    }
    return data.data
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