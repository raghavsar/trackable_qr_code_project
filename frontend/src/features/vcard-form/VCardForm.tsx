import { FC, useState } from 'react';
import { useForm } from 'react-hook-form';

interface VCardFormData {
  fullName: string;
  email?: string;
  phone?: string;
  company?: string;
  title?: string;
}

export const VCardForm: FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const { register, handleSubmit } = useForm<VCardFormData>();

  const onSubmit = async (data: VCardFormData) => {
    try {
      setIsLoading(true);
      const response = await fetch('/api/vcard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      // Handle QR code response
    } catch (error) {
      console.error('Failed to generate QR code:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* Form fields */}
    </form>
  );
}; 