import { useState, useEffect } from 'react';
import type { AnalyticsMetrics } from '@/types/analytics';

export const useAnalyticsSSE = () => {
  const [metrics, setMetrics] = useState<AnalyticsMetrics | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let eventSource: EventSource;

    const connectSSE = () => {
      eventSource = new EventSource('/analytics/api/v1/analytics/stream');

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setMetrics(data);
        } catch (err) {
          console.error('Error parsing SSE data:', err);
          setError(err instanceof Error ? err : new Error('Failed to parse analytics data'));
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE Error:', error);
        setError(error instanceof Error ? error : new Error('Analytics connection error'));
        eventSource.close();
        
        // Implement reconnection after 5 seconds
        setTimeout(connectSSE, 5000);
      };
    };

    connectSSE();

    // Cleanup on unmount
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, []);

  return { metrics, error };
};