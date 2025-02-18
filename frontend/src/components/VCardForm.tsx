import React, { useState } from 'react';
import { useQRGeneration } from '../hooks/useQRGeneration';
import { VCardData, QRGenerationError } from '../types/api';
import { PhoneNumberInput } from './PhoneNumberInput';
import { QRCodePreview } from './QRCodePreview';

interface VCardFormProps {
  onSuccess?: (qrCode: string) => void;
  className?: string;
}

export const VCardForm: React.FC<VCardFormProps> = ({
  onSuccess,
  className = ''
}) => {
  const [formData, setFormData] = useState<VCardData>({
    first_name: '',
    last_name: '',
    email: '',
    mobile_number: '',
    work_number: '',
    company: '',
    title: '',
    website: ''
  });

  const [validations, setValidations] = useState({
    mobileValid: true,
    workValid: true
  });

  const { generateQR, loading, error, clearError } = useQRGeneration();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleInputChange = (name: keyof VCardData) => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    setFormData(prev => ({
      ...prev,
      [name]: e.target.value
    }));
    setSubmitError(null);
  };

  const handlePhoneChange = (field: 'mobile_number' | 'work_number') => (
    value: string
  ) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    setSubmitError(null);
  };

  const handlePhoneValidation = (field: 'mobileValid' | 'workValid') => (
    isValid: boolean
  ) => {
    setValidations(prev => ({
      ...prev,
      [field]: isValid
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Clear previous errors
    clearError();
    setSubmitError(null);

    // Validate required fields
    if (!formData.first_name || !formData.last_name || !formData.email) {
      setSubmitError('Please fill in all required fields');
      return;
    }

    // Validate phone numbers if provided
    if (!validations.mobileValid || !validations.workValid) {
      setSubmitError('Please correct the phone number format');
      return;
    }

    try {
      const result = await generateQR({
        vcard_data: formData
      });

      if (result.qr_image_url) {
        onSuccess?.(result.qr_image_url);
      }
    } catch (err) {
      const qrError = err as QRGenerationError;
      setSubmitError(qrError.message || 'Failed to generate QR code');
    }
  };

  return (
    <div className={`max-w-2xl mx-auto p-6 ${className}`}>
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Error Display */}
        {(submitError || error) && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-red-600">
              {submitError || error?.message}
            </p>
          </div>
        )}

        {/* Personal Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              First Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="first_name"
              value={formData.first_name}
              onChange={handleInputChange('first_name')}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Last Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="last_name"
              value={formData.last_name}
              onChange={handleInputChange('last_name')}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
              required
            />
          </div>
        </div>

        {/* Contact Information */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Email <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange('email')}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
              required
            />
          </div>

          <PhoneNumberInput
            value={formData.mobile_number || ''}
            onChange={handlePhoneChange('mobile_number')}
            onValidationChange={handlePhoneValidation('mobileValid')}
            label="Mobile Number"
            className="mt-4"
          />

          <PhoneNumberInput
            value={formData.work_number || ''}
            onChange={handlePhoneChange('work_number')}
            onValidationChange={handlePhoneValidation('workValid')}
            label="Work Number"
            className="mt-4"
          />
        </div>

        {/* Company Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Company
            </label>
            <input
              type="text"
              name="company"
              value={formData.company}
              onChange={handleInputChange('company')}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Job Title
            </label>
            <input
              type="text"
              name="title"
              value={formData.title}
              onChange={handleInputChange('title')}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
            />
          </div>
        </div>

        {/* Website */}
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Website
          </label>
          <input
            type="url"
            name="website"
            value={formData.website}
            onChange={handleInputChange('website')}
            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
            placeholder="https://"
          />
        </div>

        {/* Preview */}
        <div className="mt-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Preview</h3>
          <QRCodePreview
            vcard={formData}
            className="w-64 h-64 mx-auto"
            onError={(err) => setSubmitError(err.message)}
          />
        </div>

        {/* Submit Button */}
        <div className="flex justify-end mt-6">
          <button
            type="submit"
            disabled={loading || !validations.mobileValid || !validations.workValid}
            className={`px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
              loading || !validations.mobileValid || !validations.workValid
                ? 'opacity-50 cursor-not-allowed'
                : ''
            }`}
          >
            {loading ? 'Generating...' : 'Generate QR Code'}
          </button>
        </div>
      </form>
    </div>
  );
}; 