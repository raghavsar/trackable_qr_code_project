/**
 * Phone number formatting utilities
 */

/**
 * Format phone number to E.164 format (+[country_code][number])
 * Assumes Indian numbers if no country code provided
 */
export const formatPhoneNumber = (phone: string | undefined): string => {
  if (!phone) return '';

  // Remove all non-digit characters
  const digits = phone.replace(/\D/g, '');

  // If already has country code (starts with +), just format
  if (phone.startsWith('+')) {
    return `+${digits}`;
  }

  // Remove leading 0 if exists
  const number = digits.startsWith('0') ? digits.slice(1) : digits;

  // If number starts with 91 and is correct length, assume it's already formatted
  if (number.startsWith('91') && (number.length === 12)) {
    return `+${number}`;
  }

  // For Indian numbers (assuming 10 digits), add +91
  if (number.length === 10) {
    return `+91${number}`;
  }

  // Return original number if can't determine format
  return `+${number}`;
};

/**
 * Validate phone number format and length
 */
export const validatePhoneNumber = (phone: string | undefined): { isValid: boolean; error?: string } => {
  if (!phone) {
    return { isValid: true }; // Phone is optional
  }

  const digits = phone.replace(/\D/g, '');

  // Check if number has country code
  if (!phone.startsWith('+')) {
    return { isValid: false, error: 'Phone number must start with country code (e.g., +91)' };
  }

  // Check length (international format should be 11-15 digits)
  if (digits.length < 11 || digits.length > 15) {
    return { isValid: false, error: 'Phone number must be between 11 and 15 digits including country code' };
  }

  return { isValid: true };
}; 