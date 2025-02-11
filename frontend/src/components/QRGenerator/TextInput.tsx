import React from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'react-hot-toast';

interface Props {
  onGenerate: (content: string) => Promise<void>;
}

interface FormData {
  text: string;
}

const TextInput: React.FC<Props> = ({ onGenerate }) => {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>();

  const onSubmit = async (data: FormData) => {
    try {
      await onGenerate(data.text);
    } catch (error) {
      toast.error('Failed to generate QR code');
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <textarea
          {...register('text', {
            required: 'Text is required',
            maxLength: {
              value: 1000,
              message: 'Text must be less than 1000 characters'
            }
          })}
          placeholder="Enter text"
          rows={4}
          className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
        />
        {errors.text && (
          <p className="mt-1 text-sm text-red-500">{errors.text.message}</p>
        )}
      </div>
      <button
        type="submit"
        className="w-full px-4 py-2 text-white bg-blue-500 rounded hover:bg-blue-600"
      >
        Generate QR Code
      </button>
    </form>
  );
};

export default TextInput; 