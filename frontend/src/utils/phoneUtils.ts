/**
 * Phone number formatting utilities
 */

/**
 * Format phone number to E.164 format (+[country_code][number])
 * Preserves the country code that was provided
 */
export const formatPhoneNumber = (phone: string | undefined): string => {
  if (!phone) return '';

  // If already formatted with a country code, return as is
  if (phone.match(/^\+\d+\s+\d+/)) {
    return phone;
  }

  // Remove all non-digit and non-plus characters
  let formatted = phone.replace(/[^\d+]/g, '');
  
  // Make sure there's only one + at the beginning
  formatted = formatted.replace(/\+/g, '');
  
  // If no country code, we should not normally reach here because the UI
  // now enforces a country code selection, but as a fallback:
  if (!formatted.startsWith('+')) {
    formatted = '+' + formatted;
  }
  
  return formatted;
};

/**
 * Validate phone number format and length
 */
export const validatePhoneNumber = (phone: string | undefined): { isValid: boolean; error?: string } => {
  if (!phone) {
    return { isValid: true }; // Phone is optional
  }

  // Check if number has country code
  if (!phone.includes('+')) {
    return { isValid: false, error: 'Phone number must include country code' };
  }

  // Get only the digits (excluding the +)
  const digits = phone.replace(/\D/g, '');

  // Check minimum length (should have at least a country code + local number)
  if (digits.length < 7) {
    return { isValid: false, error: 'Phone number is too short' };
  }

  // Check maximum length
  if (digits.length > 15) {
    return { isValid: false, error: 'Phone number is too long' };
  }

  return { isValid: true };
}; 