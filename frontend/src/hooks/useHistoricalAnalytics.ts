import { useState, useEffect, useCallback } from 'react';
import type { DailyMetric } from '@/types/analytics';

interface UseHistoricalAnalyticsProps {
  startDate: string;
  endDate: string;
}

const MAX_RETRIES = 3;
const RETRY_DELAY = 2000; // 2 seconds

export const useHistoricalAnalytics = ({ startDate, endDate }: UseHistoricalAnalyticsProps) => {
  const [metrics, setMetrics] = useState<DailyMetric[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasData, setHasData] = useState<boolean>(true);

  const fetchWithRetry = useCallback(async (retryCount = 0): Promise<DailyMetric[]> => {
    try {
      const response = await fetch(
        `/api/v1/analytics/metrics/daily?start_date=${startDate}&end_date=${endDate}`,
        {
          headers: {
            'Accept': 'application/json',
          },
          credentials: 'include'
        }
      );

      if (!response.ok) {
        if (response.status === 404) {
          // No data found is a valid state
          setHasData(false);
          return [];
        }
        
        // Log detailed error information for other errors
        const errorText = await response.text();
        console.error('Analytics API Error:', {
          status: response.status,
          statusText: response.statusText,
          body: errorText,
          headers: Object.fromEntries(response.headers.entries())
        });

        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      
      // Check if the response has data
      if (!data?.metrics || data.metrics.length === 0) {
        setHasData(false);
        return [];
      }

      setHasData(true);
      return data.metrics;
    } catch (err) {
      if (retryCount < MAX_RETRIES) {
        console.warn(`Retry attempt ${retryCount + 1} of ${MAX_RETRIES}`);
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
        return fetchWithRetry(retryCount + 1);
      }
      throw err;
    }
  }, [startDate, endDate]);

  useEffect(() => {
    const fetchData = async () => {
      if (!startDate || !endDate) return;
      
      try {
        setLoading(true);
        setError(null);
        
        const data = await fetchWithRetry();
        
        if (data.length === 0) {
          setMetrics([]);
          return;
        }

        // Transform and validate data
        const validatedData = data.map(metric => ({
          ...metric,
          date: new Date(metric.date).toISOString().split('T')[0], // Ensure consistent date format
          total_scans: Number(metric.total_scans) || 0,
          mobile_scans: Number(metric.mobile_scans) || 0,
          desktop_scans: Number(metric.desktop_scans) || 0,
          contact_adds: Number(metric.contact_adds) || 0,
          vcf_downloads: Number(metric.vcf_downloads) || 0
        }));

        setMetrics(validatedData);
      } catch (err) {
        console.error('Failed to fetch historical data:', err);
        setError(err instanceof Error ? err : new Error('Failed to fetch historical data'));
        setMetrics([]); // Reset metrics on error
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [fetchWithRetry]);

  return { 
    metrics, 
    error, 
    loading,
    hasData,
    refetch: useCallback(() => fetchWithRetry(), [fetchWithRetry])
  };
}; 