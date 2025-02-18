import { useState } from 'react';
import { QRDesignOptions, QRGenerateResponse, QRGenerationError, QRPreviewRequest, QRPreviewResponse } from '../types/api';

export const defaultQRStyle: QRDesignOptions = {
    box_size: 10,
    border: 4,
    foreground_color: "#000000",
    background_color: "#FFFFFF",
    eye_color: "#ff4d26",
    module_color: "#0f50b5",
    pattern_style: "dots",
    error_correction: "Q",
    logo_url: "microservices/qr-service/test/test_output/Phonon_Favicon.png",
    logo_size: 0.15,
    logo_background: true,
    logo_round: true
};

interface QRGenerationState {
    isLoading: boolean;
    error: string | null;
    qrImageUrl: string | null;
}

const useQRGeneration = () => {
    const [state, setState] = useState<QRGenerationState>({
        isLoading: false,
        error: null,
        qrImageUrl: null
    });

    const generateQR = async (vCardData: Record<string, any>, designOptions: QRDesignOptions = defaultQRStyle) => {
        setState(prev => ({ ...prev, isLoading: true, error: null }));
        try {
            const response = await fetch(`${import.meta.env.VITE_API_URL}/qr/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    vcard_data: vCardData,
                    design_options: designOptions
                } as QRPreviewRequest)
            });

            if (!response.ok) {
                const errorData: QRGenerationError = await response.json();
                throw new Error(errorData.detail || 'Failed to generate QR code');
            }

            const data: QRGenerateResponse = await response.json();
            setState(prev => ({ ...prev, qrImageUrl: data.qr_image_url, isLoading: false }));
            return data;
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to generate QR code';
            setState(prev => ({ ...prev, error: errorMessage, isLoading: false }));
            throw error;
        }
    };

    const previewQR = async (vCardData: Record<string, any>, designOptions: QRDesignOptions = defaultQRStyle) => {
        setState(prev => ({ ...prev, isLoading: true, error: null }));
        try {
            const response = await fetch(`${import.meta.env.VITE_API_URL}/qr/preview`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    vcard_data: vCardData,
                    design_options: designOptions
                } as QRPreviewRequest)
            });

            if (!response.ok) {
                const errorData: QRGenerationError = await response.json();
                throw new Error(errorData.detail || 'Failed to preview QR code');
            }

            const data: QRPreviewResponse = await response.json();
            return data.qr_image_base64;
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to preview QR code';
            setState(prev => ({ ...prev, error: errorMessage, isLoading: false }));
            throw error;
        }
    };

    return {
        ...state,
        generateQR,
        previewQR
    };
};

export default useQRGeneration; 