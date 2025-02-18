import { api } from '../lib/axios';
import {
  QRGenerateRequest,
  QRGenerateResponse,
  QRPreviewRequest,
  QRPreviewResponse,
  QRGenerationError,
  DEFAULT_PHONON_TEMPLATE
} from '../types/api';

class QRService {
  private handleError(error: any): never {
    const qrError: QRGenerationError = {
      status: error.response?.status || 500,
      message: error.response?.data?.detail || 'Failed to generate QR code',
      code: error.code,
      details: error.response?.data
    };
    throw qrError;
  }

  async generateQR(request: QRGenerateRequest): Promise<QRGenerateResponse> {
    try {
      // Always use Phonon template as base, merge with custom design if provided
      const requestWithDefaults = {
        ...request,
        design: {
          ...DEFAULT_PHONON_TEMPLATE,
          ...(request.design || {}),
        }
      };

      const response = await api.post<QRGenerateResponse>(
        '/qrcodes/generate',
        requestWithDefaults
      );

      // If the response doesn't include the full URL, construct it
      if (response.data.qr_image_url && !response.data.qr_image_url.startsWith('http')) {
        const baseUrl = process.env.REACT_APP_API_URL || '';
        response.data.qr_image_url = `${baseUrl}${response.data.qr_image_url}`;
      }

      return response.data;
    } catch (error) {
      this.handleError(error);
    }
  }

  async previewQR(request: QRPreviewRequest): Promise<QRPreviewResponse> {
    try {
      // Always use Phonon template as base, merge with custom design if provided
      const requestWithDefaults = {
        ...request,
        design: {
          ...DEFAULT_PHONON_TEMPLATE,
          ...(request.design || {}),
        }
      };

      const response = await api.post<QRPreviewResponse>(
        '/qrcodes/preview',
        requestWithDefaults
      );

      // If the response doesn't include the full URL, construct it
      if (response.data.preview_url && !response.data.preview_url.startsWith('http')) {
        const baseUrl = process.env.REACT_APP_API_URL || '';
        response.data.preview_url = `${baseUrl}${response.data.preview_url}`;
      }

      return response.data;
    } catch (error) {
      this.handleError(error);
    }
  }

  async getQRCode(id: string): Promise<QRGenerateResponse> {
    try {
      const response = await api.get<QRGenerateResponse>(`/qrcodes/${id}`);
      
      // If the response doesn't include the full URL, construct it
      if (response.data.qr_image_url && !response.data.qr_image_url.startsWith('http')) {
        const baseUrl = process.env.REACT_APP_API_URL || '';
        response.data.qr_image_url = `${baseUrl}${response.data.qr_image_url}`;
      }
      
      return response.data;
    } catch (error) {
      this.handleError(error);
    }
  }

  async deleteQRCode(id: string): Promise<void> {
    try {
      await api.delete(`/qrcodes/${id}`);
    } catch (error) {
      this.handleError(error);
    }
  }

  async updateQRCode(
    id: string,
    request: QRGenerateRequest
  ): Promise<QRGenerateResponse> {
    try {
      // Always use Phonon template as base, merge with custom design if provided
      const requestWithDefaults = {
        ...request,
        design: {
          ...DEFAULT_PHONON_TEMPLATE,
          ...(request.design || {}),
        }
      };

      const response = await api.put<QRGenerateResponse>(
        `/qrcodes/${id}`,
        requestWithDefaults
      );

      // If the response doesn't include the full URL, construct it
      if (response.data.qr_image_url && !response.data.qr_image_url.startsWith('http')) {
        const baseUrl = process.env.REACT_APP_API_URL || '';
        response.data.qr_image_url = `${baseUrl}${response.data.qr_image_url}`;
      }

      return response.data;
    } catch (error) {
      this.handleError(error);
    }
  }

  getDownloadUrl(qrCode: QRGenerateResponse): string {
    if (!qrCode.qr_image_url) return '';
    
    // If the URL doesn't start with http, prepend the API base URL
    if (!qrCode.qr_image_url.startsWith('http')) {
      const baseUrl = process.env.REACT_APP_API_URL || '';
      return `${baseUrl}${qrCode.qr_image_url}`;
    }
    
    return qrCode.qr_image_url;
  }

  getPreviewUrl(qrCode: QRGenerateResponse): string {
    return this.getDownloadUrl(qrCode);
  }
}

export const qrService = new QRService(); 