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

      // Ensure the URL is properly formatted
      if (response.data.qr_image_url) {
        // If it's already a full URL, use it as is
        if (response.data.qr_image_url.startsWith('http')) {
          // URL is already complete
        } else {
          // Add the API base URL if needed
          const baseUrl = import.meta.env.VITE_API_URL || '';
          response.data.qr_image_url = `${baseUrl}${response.data.qr_image_url}`;
        }

        // Log the final URL for debugging
        console.log('QR Image URL:', response.data.qr_image_url);
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

      // Ensure the URL is properly formatted
      if (response.data.preview_url) {
        // If it's already a full URL, use it as is
        if (response.data.preview_url.startsWith('http')) {
          // URL is already complete
        } else {
          // Add the API base URL if needed
          const baseUrl = import.meta.env.VITE_API_URL || '';
          response.data.preview_url = `${baseUrl}${response.data.preview_url}`;
        }

        // Log the final URL for debugging
        console.log('Preview URL:', response.data.preview_url);
      }

      return response.data;
    } catch (error) {
      this.handleError(error);
    }
  }

  async getQRCode(id: string): Promise<QRGenerateResponse> {
    try {
      const response = await api.get<QRGenerateResponse>(`/qrcodes/${id}`);

      // Ensure the URL is properly formatted
      if (response.data.qr_image_url) {
        // If it's already a full URL, use it as is
        if (response.data.qr_image_url.startsWith('http')) {
          // URL is already complete
        } else {
          // Add the API base URL if needed
          const baseUrl = import.meta.env.VITE_API_URL || '';
          response.data.qr_image_url = `${baseUrl}${response.data.qr_image_url}`;
        }

        // Log the final URL for debugging
        console.log('QR Image URL (get):', response.data.qr_image_url);
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

      // Ensure the URL is properly formatted
      if (response.data.qr_image_url) {
        // If it's already a full URL, use it as is
        if (response.data.qr_image_url.startsWith('http')) {
          // URL is already complete
        } else {
          // Add the API base URL if needed
          const baseUrl = import.meta.env.VITE_API_URL || '';
          response.data.qr_image_url = `${baseUrl}${response.data.qr_image_url}`;
        }

        // Log the final URL for debugging
        console.log('QR Image URL (update):', response.data.qr_image_url);
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
      const baseUrl = import.meta.env.VITE_API_URL || '';
      const url = `${baseUrl}${qrCode.qr_image_url}`;
      console.log('Download URL (constructed):', url);
      return url;
    }

    console.log('Download URL (original):', qrCode.qr_image_url);
    return qrCode.qr_image_url;
  }

  getPreviewUrl(qrCode: QRGenerateResponse): string {
    return this.getDownloadUrl(qrCode);
  }
}

export const qrService = new QRService();