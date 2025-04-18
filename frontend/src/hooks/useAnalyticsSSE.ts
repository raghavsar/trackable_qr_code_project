import { useState, useEffect, useCallback, useRef } from 'react';
import type { AnalyticsMetrics } from '@/types/analytics';
import { useNavigate } from 'react-router-dom';

const API_URL = import.meta.env.VITE_API_URL;

interface UseAnalyticsSSEProps {
  vcardId?: string;
}

interface ConnectionStatus {
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  lastHeartbeat?: string;
  clientId?: string;
  error?: string;
  reconnectAttempt: number;
  lastConnected?: string;
}

export const useAnalyticsSSE = ({ vcardId }: UseAnalyticsSSEProps = {}) => {
  const [metrics, setMetrics] = useState<AnalyticsMetrics | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    status: 'connecting',
    reconnectAttempt: 0
  });
  const [isConnected, setIsConnected] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const navigate = useNavigate();
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastHeartbeatRef = useRef<string | null>(null);

  const MAX_RETRIES = 5;
  const BASE_RETRY_DELAY = 1000; // 1 second
  const HEARTBEAT_TIMEOUT = 30000; // 30 seconds

  // Function to fetch initial metrics
  const fetchInitialMetrics = async () => {
    try {
      // Determine the correct endpoint based on whether we have a vcardId
      // Check if API_URL already contains '/api'
      const apiPath = API_URL.endsWith('/api') ? `${API_URL}/v1` : `${API_URL}/api/v1`;

      const endpoint = vcardId
        ? `${apiPath}/analytics/vcard/${vcardId}?timeRange=30d`
        : `${apiPath}/analytics/metrics?timeRange=30d`;

      console.log(`📊 Fetching initial metrics from endpoint: ${endpoint}`);

      const token = localStorage.getItem('token');
      if (!token) {
        console.error('❌ No authentication token found');
        setError(new Error('Authentication required'));
        return;
      }

      // Add retry logic for initial data fetch
      let retries = 0;
      const maxRetries = 3;

      while (retries < maxRetries) {
        try {
          const response = await fetch(
            endpoint,
            {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            }
          );

          if (!response.ok) {
            console.error(`❌ HTTP error fetching initial metrics: ${response.status} ${response.statusText}`);
            if (response.status === 401) {
              // Handle unauthorized access
              localStorage.removeItem('token');
              navigate('/login');
              throw new Error('Authentication expired. Please log in again.');
            }
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          const data = await response.json();
          console.log('📊 Initial metrics data received:', data);

          // If we get here, the fetch was successful

          // Ensure the data is properly structured before setting state
          if (data) {
            setMetrics(prevMetrics => {
              const newMetrics = {
                ...prevMetrics,
                ...data,
                // Explicitly set the critical fields
                total_scans: data.total_scans ?? prevMetrics?.total_scans ?? 0,
                mobile_scans: data.mobile_scans ?? prevMetrics?.mobile_scans ?? 0,
                contact_adds: data.contact_adds ?? prevMetrics?.contact_adds ?? 0,
                vcf_downloads: data.vcf_downloads ?? prevMetrics?.vcf_downloads ?? 0,
                recent_scans: Array.isArray(data.recent_scans)
                  ? data.recent_scans
                  : prevMetrics?.recent_scans ?? []
              };
              console.log('📊 Initial metrics state set to:', newMetrics);
              return newMetrics;
            });

            // Exit the retry loop if successful
            break;
          } else {
            console.error('❌ Initial metrics data is empty or invalid:', data);
            throw new Error('Invalid metrics data received');
          }
        } catch (fetchError) {
          retries++;
          console.warn(`⚠️ Retry ${retries}/${maxRetries} for initial metrics failed:`, fetchError);

          if (retries >= maxRetries) {
            console.error(`❌ All ${maxRetries} retries failed. Giving up.`);
            throw fetchError;
          }

          // Exponential backoff delay
          const delay = 1000 * Math.pow(2, retries);
          console.log(`⏱️ Waiting ${delay}ms before retry...`);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    } catch (err) {
      console.error('❌ Failed to fetch initial metrics:', err);
      setError(err instanceof Error ? err : new Error('Failed to fetch metrics'));
    }
  };

  // Function to handle SSE events
  const handleSSEEvent = useCallback((event: MessageEvent) => {
    try {
      console.log(`📨 SSE event received: ${event.type}`, event);

      // Reset heartbeat timeout on any event
      if (heartbeatTimeoutRef.current) {
        clearTimeout(heartbeatTimeoutRef.current);
      }

      // Set new heartbeat timeout
      heartbeatTimeoutRef.current = setTimeout(() => {
        console.warn('⚠️ No heartbeat received in the last 30 seconds');
        setConnectionStatus(prev => ({
          ...prev,
          status: 'disconnected',
          error: 'Connection timeout - no heartbeat received'
        }));

        // Attempt to reconnect
        reconnectSSE();
      }, HEARTBEAT_TIMEOUT);

      // Handle different event types
      switch (event.type) {
        case 'metrics':
          try {
            const parsedData = JSON.parse(event.data);
            console.log('📊 Metrics data received (RAW):', event.data);
            console.log('📊 Metrics data parsed:', parsedData);

            // Simple extraction of metrics data - no longer looking for nested structures
            // since we fixed the backend to always send metrics at the root level
            setMetrics(prevMetrics => {
              const newMetrics = {
                ...prevMetrics,
                ...parsedData,
                // Ensure critical fields are updated, defaulting to previous values if not in the new data
                total_scans: parsedData.total_scans ?? prevMetrics?.total_scans ?? 0,
                mobile_scans: parsedData.mobile_scans ?? prevMetrics?.mobile_scans ?? 0,
                contact_adds: parsedData.contact_adds ?? prevMetrics?.contact_adds ?? 0,
                vcf_downloads: parsedData.vcf_downloads ?? prevMetrics?.vcf_downloads ?? 0,
                recent_scans: Array.isArray(parsedData.recent_scans)
                  ? parsedData.recent_scans
                  : prevMetrics?.recent_scans ?? []
              };

              console.log('📊 New metrics state after update:', newMetrics);
              return newMetrics;
            });
          } catch (err) {
            console.error('❌ Error parsing metrics data:', err, 'Raw data:', event.data);
          }
          break;

        case 'heartbeat':
          const heartbeatData = JSON.parse(event.data);
          console.log('💓 Heartbeat received:', heartbeatData);
          lastHeartbeatRef.current = heartbeatData.timestamp;
          setConnectionStatus(prev => ({
            ...prev,
            status: 'connected',
            lastHeartbeat: heartbeatData.timestamp
          }));
          break;

        case 'connection':
          const connectionData = JSON.parse(event.data);
          console.log('🔌 Connection event:', connectionData);
          setConnectionStatus(prev => ({
            ...prev,
            status: 'connected',
            clientId: connectionData.client_id,
            lastConnected: new Date().toISOString(),
            reconnectAttempt: 0
          }));
          break;

        case 'disconnection':
          const disconnectionData = JSON.parse(event.data);
          console.log('🔌 Disconnection event:', disconnectionData);
          setConnectionStatus(prev => ({
            ...prev,
            status: 'disconnected'
          }));
          break;

        case 'error':
          const errorData = JSON.parse(event.data);
          console.error('❌ Error event received:', errorData);
          setConnectionStatus(prev => ({
            ...prev,
            status: 'error',
            error: errorData.error
          }));
          break;

        case 'message':
          try {
            // Default message event (for backward compatibility)
            const data = JSON.parse(event.data);
            console.log('📨 Default message event data (RAW):', event.data);

            // Similar simplified extraction for message events
            setMetrics(prevMetrics => {
              const newMetrics = {
                ...prevMetrics,
                ...data,
                // Ensure critical fields are updated
                total_scans: data.total_scans ?? prevMetrics?.total_scans ?? 0,
                mobile_scans: data.mobile_scans ?? prevMetrics?.mobile_scans ?? 0,
                contact_adds: data.contact_adds ?? prevMetrics?.contact_adds ?? 0,
                vcf_downloads: data.vcf_downloads ?? prevMetrics?.vcf_downloads ?? 0,
                recent_scans: Array.isArray(data.recent_scans)
                  ? data.recent_scans
                  : prevMetrics?.recent_scans ?? []
              };

              console.log('📨 New metrics state after message update:', newMetrics);
              return newMetrics;
            });
          } catch (err) {
            console.error('❌ Error parsing message data:', err, 'Raw data:', event.data);
          }
          break;

        default:
          console.warn(`⚠️ Unknown event type: ${event.type}`);
      }
    } catch (err) {
      console.error('❌ Error handling SSE event:', err);
      console.error('Raw event data that caused error:', event.data);
    }
  }, []);

  // Function to reconnect SSE
  const reconnectSSE = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (retryCount >= MAX_RETRIES) {
      console.error(`❌ Maximum retry attempts (${MAX_RETRIES}) reached`);
      setConnectionStatus(prev => ({
        ...prev,
        status: 'error',
        error: `Failed to connect after ${MAX_RETRIES} attempts`
      }));
      return;
    }

    const delay = BASE_RETRY_DELAY * Math.pow(2, retryCount);
    console.log(`🔄 Scheduling reconnect in ${delay}ms (attempt ${retryCount + 1}/${MAX_RETRIES})`);

    reconnectTimeoutRef.current = setTimeout(() => {
      setRetryCount(prev => prev + 1);
      connectSSE();
    }, delay);
  }, [retryCount]);

  // Function to connect to SSE
  const connectSSE = useCallback(() => {
    // Clean up existing connection if any
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    try {
      setConnectionStatus(prev => ({
        ...prev,
        status: 'connecting'
      }));

      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Authentication required');
      }

      // Determine SSE endpoint based on vcardId
      // Check if API_URL already contains '/api'
      const apiPath = API_URL.endsWith('/api') ? `${API_URL}/v1` : `${API_URL}/api/v1`;

      const sseEndpoint = vcardId
        ? `${apiPath}/analytics/vcard/${vcardId}/stream`
        : `${apiPath}/analytics/stream`;

      console.log(`🔌 Connecting to SSE endpoint: ${sseEndpoint}`);

      // Create URL with auth token in the query parameter
      const url = new URL(sseEndpoint);
      url.searchParams.append('token', token);

      // Create new EventSource with the token in the URL
      const eventSource = new EventSource(url.toString());
      eventSourceRef.current = eventSource;

      // Set up event listeners
      eventSource.onopen = (e) => {
        console.log('🔌 SSE connection opened:', e);
        setConnectionStatus(prev => ({
          ...prev,
          status: 'connected',
          lastConnected: new Date().toISOString(),
          error: undefined
        }));
        setIsConnected(true);
        setRetryCount(0);
      };

      eventSource.onerror = (e) => {
        console.error('❌ SSE connection error:', e);
        setConnectionStatus(prev => ({
          ...prev,
          status: 'error',
          error: 'Connection error'
        }));
        setIsConnected(false);

        // Close and attempt to reconnect
        eventSource.close();
        eventSourceRef.current = null;
        reconnectSSE();
      };

      // Set up message event listeners using addEventListener instead of onmessage
      eventSource.addEventListener('message', handleSSEEvent);
      eventSource.addEventListener('metrics', handleSSEEvent);
      eventSource.addEventListener('heartbeat', handleSSEEvent);
      eventSource.addEventListener('connection', handleSSEEvent);
      eventSource.addEventListener('error', handleSSEEvent);

      // Set heartbeat timeout
      if (heartbeatTimeoutRef.current) {
        clearTimeout(heartbeatTimeoutRef.current);
      }

      heartbeatTimeoutRef.current = setTimeout(() => {
        console.warn('⚠️ Initial heartbeat timeout');
        setConnectionStatus(prev => ({
          ...prev,
          status: 'error',
          error: 'No initial heartbeat received'
        }));

        // Close and reconnect
        eventSource.close();
        eventSourceRef.current = null;
        reconnectSSE();
      }, HEARTBEAT_TIMEOUT);
    } catch (err) {
      console.error('❌ Error creating SSE connection:', err);
      setError(err instanceof Error ? err : new Error('Failed to connect to analytics stream'));
      setConnectionStatus(prev => ({
        ...prev,
        status: 'error',
        error: err instanceof Error ? err.message : 'Unknown error',
        reconnectAttempt: prev.reconnectAttempt + 1
      }));
      setIsConnected(false);

      // Schedule reconnect
      reconnectSSE();
    }
  }, [vcardId, handleSSEEvent]);

  // Setup and cleanup effect
  useEffect(() => {
    console.log('🚀 Initializing Analytics SSE hook');

    // First fetch initial metrics
    fetchInitialMetrics();

    // Then establish SSE connection
    connectSSE();

    // Cleanup function
    return () => {
      console.log('🧹 Cleaning up Analytics SSE connections');

      if (eventSourceRef.current) {
        console.log('🔌 Closing SSE connection');
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      if (heartbeatTimeoutRef.current) {
        clearTimeout(heartbeatTimeoutRef.current);
        heartbeatTimeoutRef.current = null;
      }
    };
  }, [vcardId]); // Re-initialize when vcardId changes

  return {
    metrics,
    error,
    isConnected,
    connectionStatus,
    refetch: fetchInitialMetrics
  };
};