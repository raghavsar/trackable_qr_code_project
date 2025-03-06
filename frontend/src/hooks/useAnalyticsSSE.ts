import { useState, useEffect } from 'react';
import type { AnalyticsMetrics } from '@/types/analytics';
import { useNavigate } from 'react-router-dom';

const API_URL = import.meta.env.VITE_API_URL;

interface UseAnalyticsSSEProps {
  qrId?: string;
}

export const useAnalyticsSSE = ({ qrId }: UseAnalyticsSSEProps = {}) => {
  const [metrics, setMetrics] = useState<AnalyticsMetrics | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const navigate = useNavigate();

  // Function to fetch initial metrics
  const fetchInitialMetrics = async () => {
    try {
      const response = await fetch(
        `${API_URL}/api/v1/analytics/qr/${qrId}?timeRange=30d`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setMetrics(data);
    } catch (err) {
      console.error('Failed to fetch initial metrics:', err);
      setError(err instanceof Error ? err : new Error('Failed to fetch metrics'));
    }
  };

  useEffect(() => {
    let eventSource: EventSource;
    let reconnectTimeout: NodeJS.Timeout;

    const connectSSE = () => {
      try {
        // Close existing connection if any
        if (eventSource) {
          console.log('Closing existing SSE connection');
          eventSource.close();
        }

        // Get the authentication token
        const token = localStorage.getItem('token');
        if (!token) {
          console.error('No authentication token found');
          navigate('/login');
          return;
        }

        // Create new connection with full URL
        const baseUrl = qrId 
          ? `/analytics/qr/${qrId}/stream`
          : `/analytics/stream`;

        // Ensure we're using the correct API URL and construct the full URL
        const fullUrl = `${API_URL}/api/v1${baseUrl}`;
        const url = new URL(fullUrl);
        url.searchParams.append('access_token', token);

        console.log('🔑 Token:', token.substring(0, 10) + '...');
        console.log('🌐 Base API URL:', API_URL);
        console.log('🔗 Full SSE URL:', url.toString());
        console.log('🚀 Attempting to connect to SSE stream...');
        
        eventSource = new EventSource(url.toString(), { withCredentials: true });
        
        eventSource.onopen = () => {
          console.log('✅ SSE Connection established successfully');
          setIsConnected(true);
          setError(null);
          // Fetch initial metrics when connection is established
          fetchInitialMetrics();
        };

        eventSource.onmessage = (event) => {
          try {
            console.log('📨 Raw SSE data received:', event.data);
            const data = JSON.parse(event.data);
            console.log('📊 Parsed SSE data:', data);
            
            // Update metrics state with the new data
            setMetrics(prevMetrics => {
              if (!prevMetrics) return data;
              
              const newMetrics = {
                ...prevMetrics,
                ...data,
                total_scans: data.total_scans ?? prevMetrics.total_scans,
                contact_adds: data.contact_adds ?? prevMetrics.contact_adds,
                vcf_downloads: data.vcf_downloads ?? prevMetrics.vcf_downloads,
                recent_scans: Array.isArray(data.recent_scans) ? data.recent_scans : prevMetrics.recent_scans
              };
              console.log('🔄 Updated metrics state:', newMetrics);
              return newMetrics;
            });
          } catch (err) {
            console.error('❌ Error parsing SSE data:', err);
            console.error('Raw data that caused error:', event.data);
          }
        };

        eventSource.onerror = (error) => {
          console.error('❌ SSE Connection error:', error);
          console.error('EventSource readyState:', eventSource.readyState);
          console.error('Attempted URL:', url.toString());
          setIsConnected(false);
          
          if (eventSource.readyState === EventSource.CLOSED) {
            console.log('🔄 Connection closed, attempting to reconnect...');
            eventSource.close();
            reconnectTimeout = setTimeout(connectSSE, 5000);
          }
        };
      } catch (err) {
        console.error('❌ Error establishing SSE connection:', err);
        setIsConnected(false);
        reconnectTimeout = setTimeout(connectSSE, 5000);
      }
    };

    // Start the connection
    console.log('🚀 Initializing SSE connection for QR ID:', qrId);
    connectSSE();

    // Cleanup function
    return () => {
      if (eventSource) {
        console.log('🛑 Cleaning up SSE connection');
        eventSource.close();
        setIsConnected(false);
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, [qrId, navigate]); // Dependencies

  return { metrics, error, isConnected };
};