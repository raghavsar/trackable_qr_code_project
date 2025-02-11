import * as React from 'react'
import type { QRCodeResponse } from '../../types/api'

interface Props {
  data: QRCodeResponse
  onSave: () => Promise<void>
  onDownload: () => void
}

export const QRPreview: React.FC<Props> = ({ data, onSave, onDownload }) => {
  return (
    <div className="flex flex-col items-center space-y-4 p-4 border rounded">
      <img
        src={data.qr_image_url}
        alt="QR Code"
        className="w-64 h-64"
      />
      <div className="flex space-x-4">
        <button
          onClick={onSave}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Save QR Code
        </button>
        <button
          onClick={onDownload}
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
        >
          Download
        </button>
      </div>
      <div className="text-sm text-gray-500">
        Tracking ID: {data.tracking_id}
      </div>
    </div>
  );
}; 