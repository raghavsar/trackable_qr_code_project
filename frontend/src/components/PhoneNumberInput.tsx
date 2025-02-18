import React, { useState, useEffect } from 'react';
import { formatPhoneNumber, validatePhoneNumber } from '../utils/phoneUtils';

interface PhoneNumberInputProps {
  value: string;
  onChange: (value: string) => void;
  onValidationChange?: (isValid: boolean) => void;
  label?: string;
  placeholder?: string;
  required?: boolean;
  className?: string;
  name?: string;
}

export const PhoneNumberInput: React.FC<PhoneNumberInputProps> = ({
  value,
  onChange,
  onValidationChange,
  label = 'Phone Number',
  placeholder = '+91 XXXXX XXXXX',
  required = false,
  className = '',
  name
}) => {
  const [error, setError] = useState<string | undefined>();
  const [isTouched, setIsTouched] = useState(false);

  useEffect(() => {
    if (isTouched || required) {
      const { isValid, error } = validatePhoneNumber(value);
      setError(error);
      onValidationChange?.(isValid);
    }
  }, [value, isTouched, required, onValidationChange]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneNumber(e.target.value);
    onChange(formatted);
  };

  const handleBlur = () => {
    setIsTouched(true);
    const formatted = formatPhoneNumber(value);
    onChange(formatted);
  };

  return (
    <div className={`flex flex-col ${className}`}>
      <label className="mb-1 text-sm font-medium text-gray-700">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <input
        type="tel"
        name={name}
        value={value}
        onChange={handleChange}
        onBlur={handleBlur}
        placeholder={placeholder}
        className={`px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
          error
            ? 'border-red-300 focus:ring-red-200'
            : 'border-gray-300 focus:ring-blue-200'
        }`}
      />
      {error && isTouched && (
        <p className="mt-1 text-sm text-red-500">{error}</p>
      )}
    </div>
  );
}; 