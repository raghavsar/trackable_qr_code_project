import React, { useEffect } from 'react';
import { useQRGeneration } from '../hooks/useQRGeneration';
import { QRDesignOptions, VCardData, DEFAULT_PHONON_TEMPLATE } from '../types/api';

interface QRCodePreviewProps {
  vcard: VCardData;
  design?: QRDesignOptions;
  onError?: (error: any) => void;
  className?: string;
}

export const QRCodePreview: React.FC<QRCodePreviewProps> = ({
  vcard,
  design = DEFAULT_PHONON_TEMPLATE,
  onError,
  className = ''
}) => {
  const { loading, error, preview, previewQR } = useQRGeneration();

  useEffect(() => {
    const generatePreview = async () => {
      try {
        await previewQR({
          vcard_data: vcard,
          design: {
            ...DEFAULT_PHONON_TEMPLATE,  // Start with default Phonon template
            ...design,  // Override with any custom design options
          }
        });
      } catch (err) {
        onError?.(err);
      }
    };

    if (vcard.first_name && vcard.last_name && vcard.email) {
      generatePreview();
    }
  }, [vcard, design, previewQR, onError]);

  if (loading) {
    return (
      <div className={`flex items-center justify-center p-4 ${className}`}>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex items-center justify-center p-4 text-red-500 ${className}`}>
        {error.message}
      </div>
    );
  }

  if (!preview?.preview_url) {
    return (
      <div className={`flex items-center justify-center p-4 text-gray-500 ${className}`}>
        Fill in required fields to preview QR code
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <img
        src={preview.preview_url}
        alt="QR Code Preview"
        className="w-full h-full object-contain"
        onError={(e) => {
          const img = e.target as HTMLImageElement;
          img.onerror = null; // Prevent infinite loop
          onError?.({ message: 'Failed to load QR code preview' });
        }}
      />
      {preview.api_source === 'local' && (
        <div className="absolute bottom-0 left-0 right-0 bg-yellow-100 text-yellow-800 text-xs p-1 text-center">
          Using local generation (GoQR API unavailable)
        </div>
      )}
    </div>
  );
}; 