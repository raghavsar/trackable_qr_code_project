import React, { useState, useEffect } from 'react';
import { formatPhoneNumber, validatePhoneNumber } from '../utils/phoneUtils';
import { ChevronDown } from 'lucide-react';

// Common country codes for the dropdown
const COUNTRY_CODES = [
  { code: 'US', flag: '🇺🇸', dial: '+1' },
  { code: 'GB', flag: '🇬🇧', dial: '+44' },
  { code: 'IN', flag: '🇮🇳', dial: '+91' },
  { code: 'CA', flag: '🇨🇦', dial: '+1' },
  { code: 'AU', flag: '🇦🇺', dial: '+61' },
  { code: 'DE', flag: '🇩🇪', dial: '+49' },
  { code: 'FR', flag: '🇫🇷', dial: '+33' },
  { code: 'JP', flag: '🇯🇵', dial: '+81' },
  { code: 'CN', flag: '🇨🇳', dial: '+86' },
  { code: 'BR', flag: '🇧🇷', dial: '+55' },
  { code: 'RU', flag: '🇷🇺', dial: '+7' },
  { code: 'AE', flag: '🇦🇪', dial: '+971' },
  { code: 'SG', flag: '🇸🇬', dial: '+65' },
];

interface PhoneNumberInputProps {
  value: string;
  onChange: (value: string) => void;
  onValidationChange?: (isValid: boolean) => void;
  label?: string;
  placeholder?: string;
  required?: boolean;
  className?: string;
  name?: string;
  id?: string;
  hideLabel?: boolean;
}

export const PhoneNumberInput: React.FC<PhoneNumberInputProps> = ({
  value,
  onChange,
  onValidationChange,
  label = 'Phone Number',
  placeholder = 'XXXXX XXXXX',
  required = false,
  className = '',
  name,
  id,
  hideLabel = false
}) => {
  const [error, setError] = useState<string | undefined>();
  const [isTouched, setIsTouched] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  // Extract country code from the phone number or default to +91 (India)
  const getDialCode = (phoneNumber: string) => {
    if (!phoneNumber) return '+91'; // Default to India
    const match = phoneNumber.match(/^\+(\d+)/);
    if (match) {
      const dialCode = '+' + match[1];
      const country = COUNTRY_CODES.find(c => phoneNumber.startsWith(c.dial));
      return country ? country.dial : dialCode;
    }
    return '+91'; // Default if no dial code found
  };

  const [selectedCountry, setSelectedCountry] = useState(() => {
    const dialCode = getDialCode(value);
    return COUNTRY_CODES.find(c => c.dial === dialCode) || COUNTRY_CODES[2]; // Default to India
  });

  const getPhoneWithoutDialCode = (phoneNumber: string) => {
    if (!phoneNumber) return '';
    // Remove the country code if it exists
    return phoneNumber.replace(/^\+\d+\s*/, '');
  };

  useEffect(() => {
    if (isTouched || required) {
      const { isValid, error } = validatePhoneNumber(value);
      setError(error);
      onValidationChange?.(isValid);
    }
  }, [value, isTouched, required, onValidationChange]);

  const handleCountryChange = (country: typeof COUNTRY_CODES[0]) => {
    setSelectedCountry(country);
    setIsDropdownOpen(false);

    // Get the phone number without dial code
    const phoneWithoutDialCode = getPhoneWithoutDialCode(value);

    // Update with new country code
    const newValue = phoneWithoutDialCode ? `${country.dial} ${phoneWithoutDialCode}` : '';
    onChange(newValue);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Get input value without the country code
    const inputValue = e.target.value;

    // Format the phone number but preserve the selected country code
    const formattedNumber = selectedCountry.dial + ' ' + inputValue.replace(/^\+\d+\s*/, '');
    onChange(formatPhoneNumber(formattedNumber));
  };

  const handleBlur = () => {
    setIsTouched(true);
    setIsDropdownOpen(false);
    const formatted = formatPhoneNumber(value);
    onChange(formatted);
  };

  return (
    <div className={`flex flex-col ${className}`}>
      {!hideLabel && (
        <label className="mb-1 text-sm font-medium text-gray-700">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      <div className="flex">
        <div className="relative">
          <button
            type="button"
            className="flex items-center justify-between px-3 py-2 border rounded-l-md bg-gray-50 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-200"
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          >
            <span className="flex items-center space-x-1">
              <span>{selectedCountry.flag}</span>
              <span className="text-sm font-medium">{selectedCountry.dial}</span>
            </span>
            <ChevronDown className="h-4 w-4 ml-1 text-gray-500" />
          </button>

          {isDropdownOpen && (
            <div className="absolute z-10 mt-1 w-60 max-h-80 overflow-y-auto bg-white rounded-md shadow-lg border border-gray-200">
              <div className="p-2">
                {COUNTRY_CODES.map((country) => (
                  <button
                    key={country.code}
                    type="button"
                    className="flex items-center w-full px-3 py-2 text-left text-sm hover:bg-gray-100 rounded-md"
                    onClick={() => handleCountryChange(country)}
                  >
                    <span className="mr-2 text-lg">{country.flag}</span>
                    <span className="ml-auto text-gray-500">{country.dial}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <input
          type="tel"
          name={name}
          value={getPhoneWithoutDialCode(value)}
          onChange={handleChange}
          onBlur={handleBlur}
          placeholder={placeholder}
          className={`flex-1 px-3 py-2 border rounded-r-md focus:outline-none focus:ring-2 ${
            error
              ? 'border-red-300 focus:ring-red-200'
              : 'border-gray-300 focus:ring-blue-200'
          }`}
        />
      </div>

      {error && isTouched && (
        <p className="mt-1 text-sm text-red-500">{error}</p>
      )}
    </div>
  );
}; 