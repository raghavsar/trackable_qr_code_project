// Utility functions for analytics tracking

// Track recent events to prevent duplicates
const recentEvents = new Map<string, number>();
const DEDUPLICATION_WINDOW = 5000; // 5 seconds window for deduplication

// Track if this page has been viewed in this session
const pageVisited = new Map<string, boolean>();

// Constants for tracking actions
const ACTION_SCAN = 'scan';
const ACTION_PAGE_VIEW = 'page_view';
const ACTION_CONTACT_ADD = 'contact_add';
const ACTION_VCF_DOWNLOAD = 'vcf_download';

/**
 * Check if the page is visible (not in a background tab)
 */
const isPageVisible = (): boolean => {
  return document.visibilityState === 'visible';
};

/**
 * Reset the visit tracking for a vcard (e.g., when scanned again)
 */
const resetVisitTracking = (vcardId: string): void => {
  const key = `visited-${vcardId}`;
  pageVisited.delete(key);
};

/**
 * Track an analytics event with deduplication
 */
export const trackEvent = async (
  vcardId: string | undefined,
  userId: string | undefined,
  actionType: 'scan' | 'contact_add' | 'vcf_download' | 'page_view'
): Promise<boolean> => {
  try {
    // Validate inputs
    if (!vcardId || !userId) {
      console.warn(`📊 Cannot track ${actionType} event: Missing vcardId or userId`);
      return false;
    }

    // Skip tracking if page is not visible and this is not a user-initiated action
    if (!isPageVisible() && (actionType === ACTION_PAGE_VIEW || actionType === ACTION_SCAN)) {
      console.log(`📊 Skipping ${actionType} event - page not visible`);
      return false;
    }

    // Create a unique key for this event
    const eventKey = `${vcardId}-${actionType}-${userId}`;
    const now = Date.now();

    // Check if we've seen this event recently (prevent rapid duplicates)
    const lastTracked = recentEvents.get(eventKey);
    if (lastTracked && now - lastTracked < DEDUPLICATION_WINDOW) {
      console.log(`📊 Skipping duplicate ${actionType} event for VCard ${vcardId}`);
      return false;
    }

    // Mark this event as tracked
    recentEvents.set(eventKey, now);

    // Clean up old events to prevent memory leaks
    setTimeout(() => {
      recentEvents.delete(eventKey);
    }, DEDUPLICATION_WINDOW);

    // Prepare device info
    const deviceInfo = {
      is_mobile: /Mobi|Android/i.test(navigator.userAgent),
      device: navigator.platform,
      os: navigator.platform,
      browser: navigator.userAgent
    };

    // Send the analytics event
    const apiUrl = import.meta.env.VITE_API_URL;
    console.log(`📊 Tracking ${actionType} event for VCard ${vcardId}`);

    // Ensure apiUrl is defined
    if (!apiUrl) {
      console.error('API URL is not defined');
      return false;
    }

    // Check if apiUrl already contains '/api'
    const endpoint = apiUrl.endsWith('/api')
      ? `${apiUrl}/v1/analytics/scan`
      : `${apiUrl}/api/v1/analytics/scan`;

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        vcard_id: vcardId,
        user_id: userId,
        timestamp: new Date().toISOString(),
        device_info: deviceInfo,
        action_type: actionType,
        success: true,
        ip_address: null,
        headers: {
          'user-agent': navigator.userAgent
        }
      })
    });

    if (!response.ok) {
      console.error(`Failed to track ${actionType} event:`, await response.text());
      return false;
    }

    return true;
  } catch (error) {
    console.error(`Failed to track ${actionType} event:`, error);
    return false;
  }
};

/**
 * Handle tracking for a VCard page load
 *
 * This handles the different scenarios:
 * 1. First load from QR scan: Track both scan and page_view
 * 2. First load from direct navigation: Track only page_view
 * 3. Reload of existing page: Track only page_view
 */
export const trackVCardPageLoad = async (
  vcardId: string | undefined,
  userId: string | undefined,
  isQRCodeScan: boolean
): Promise<void> => {
  if (!vcardId || !userId || !isPageVisible()) return;

  // If this is from a QR code scan, always track as a new scan
  // and reset the visit tracking
  if (isQRCodeScan) {
    console.log('📊 Tracking QR code scan');
    resetVisitTracking(vcardId);
    await trackEvent(vcardId, userId, ACTION_SCAN);
  }

  // Always track page view for any visible page load
  await trackEvent(vcardId, userId, ACTION_PAGE_VIEW);
};

/**
 * Track a contact add event (user-initiated action)
 */
export const trackContactAdd = (vcardId: string | undefined, userId: string | undefined): Promise<boolean> => {
  return trackEvent(vcardId, userId, ACTION_CONTACT_ADD);
};

/**
 * Track a VCF download event (user-initiated action)
 */
export const trackVcfDownload = (vcardId: string | undefined, userId: string | undefined): Promise<boolean> => {
  return trackEvent(vcardId, userId, ACTION_VCF_DOWNLOAD);
};

// Reset visited status on page refresh
window.addEventListener('beforeunload', () => {
  pageVisited.clear();
});