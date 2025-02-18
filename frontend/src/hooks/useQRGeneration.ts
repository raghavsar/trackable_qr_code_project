import { useState } from 'react';
import { qrService } from '../services/qrService';
import {
  QRGenerateRequest,
  QRGenerateResponse,
  QRGenerationError,
  QRPreviewRequest,
  QRPreviewResponse
} from '../types/api';

interface QRGenerationState {
  loading: boolean;
  error: QRGenerationError | null;
  qrCode: QRGenerateResponse | null;
  preview: QRPreviewResponse | null;
}

export function useQRGeneration() {
  const [state, setState] = useState<QRGenerationState>({
    loading: false,
    error: null,
    qrCode: null,
    preview: null
  });

  const generateQR = async (request: QRGenerateRequest) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const qrCode = await qrService.generateQR(request);
      setState(prev => ({ ...prev, loading: false, qrCode }));
      return qrCode;
    } catch (error) {
      const qrError = error as QRGenerationError;
      setState(prev => ({ ...prev, loading: false, error: qrError }));
      throw qrError;
    }
  };

  const previewQR = async (request: QRPreviewRequest) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const preview = await qrService.previewQR(request);
      setState(prev => ({ ...prev, loading: false, preview }));
      return preview;
    } catch (error) {
      const qrError = error as QRGenerationError;
      setState(prev => ({ ...prev, loading: false, error: qrError }));
      throw qrError;
    }
  };

  const updateQR = async (id: string, request: QRGenerateRequest) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const qrCode = await qrService.updateQRCode(id, request);
      setState(prev => ({ ...prev, loading: false, qrCode }));
      return qrCode;
    } catch (error) {
      const qrError = error as QRGenerationError;
      setState(prev => ({ ...prev, loading: false, error: qrError }));
      throw qrError;
    }
  };

  const deleteQR = async (id: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      await qrService.deleteQRCode(id);
      setState(prev => ({ ...prev, loading: false, qrCode: null }));
    } catch (error) {
      const qrError = error as QRGenerationError;
      setState(prev => ({ ...prev, loading: false, error: qrError }));
      throw qrError;
    }
  };

  const getQR = async (id: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const qrCode = await qrService.getQRCode(id);
      setState(prev => ({ ...prev, loading: false, qrCode }));
      return qrCode;
    } catch (error) {
      const qrError = error as QRGenerationError;
      setState(prev => ({ ...prev, loading: false, error: qrError }));
      throw qrError;
    }
  };

  const clearError = () => {
    setState(prev => ({ ...prev, error: null }));
  };

  const reset = () => {
    setState({
      loading: false,
      error: null,
      qrCode: null,
      preview: null
    });
  };

  return {
    ...state,
    generateQR,
    previewQR,
    updateQR,
    deleteQR,
    getQR,
    clearError,
    reset
  };
} 