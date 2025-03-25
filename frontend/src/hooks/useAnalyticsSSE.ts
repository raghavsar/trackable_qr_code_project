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
      const endpoint = vcardId 
        ? `${API_URL}/api/v1/analytics/vcard/${vcardId}?timeRange=30d`
        : `${API_URL}/api/v1/analytics/metrics?timeRange=30d`;
      
      console.log(`📊 Fetching initial metrics from endpoint: ${endpoint}`);
      
      const response = await fetch(
        endpoint,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      
      if (!response.ok) {
        console.error(`❌ HTTP error fetching initial metrics: ${response.status} ${response.statusText}`);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('📊 Initial metrics data received:', data);
      
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
      } else {
        console.error('❌ Initial metrics data is empty or invalid:', data);
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
    try {
      // Close existing connection if any
      if (eventSourceRef.current) {
        console.log('🔌 Closing existing SSE connection');
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      // Get the authentication token
      const token = localStorage.getItem('token');
      if (!token) {
        console.error('🔑 No authentication token found');
        setError(new Error('No authentication token found'));
        setConnectionStatus(prev => ({
          ...prev,
          status: 'error',
          error: 'No authentication token found'
        }));
        navigate('/login');
        return;
      }

      // Determine the correct SSE endpoint based on whether we have a vcardId
      const baseUrl = vcardId 
        ? `/api/v1/analytics/vcard/${vcardId}/stream`
        : `/api/v1/analytics/stream`;

      // Ensure we're using the correct API URL and construct the full URL
      const fullUrl = `${API_URL}${baseUrl}`;
      const url = new URL(fullUrl);
      url.searchParams.append('access_token', token);

      console.log('🔑 Token:', token.substring(0, 10) + '...');
      console.log('🌐 Base API URL:', API_URL);
      console.log('🔗 Full SSE URL:', url.toString());
      console.log('🚀 Attempting to connect to SSE stream...');
      
      setConnectionStatus(prev => ({
        ...prev,
        status: 'connecting',
        reconnectAttempt: retryCount + 1
      }));
      
      // Create new EventSource
      const eventSource = new EventSource(url.toString(), { withCredentials: true });
      eventSourceRef.current = eventSource;
      
      console.log('📡 EventSource created with readyState:', eventSource.readyState);
      
      // Add event listeners for different event types
      eventSource.addEventListener('metrics', handleSSEEvent);
      eventSource.addEventListener('heartbeat', handleSSEEvent);
      eventSource.addEventListener('connection', handleSSEEvent);
      eventSource.addEventListener('disconnection', handleSSEEvent);
      eventSource.addEventListener('error', handleSSEEvent);
      
      // Default message handler (for backward compatibility)
      eventSource.onmessage = handleSSEEvent;
      
      eventSource.onopen = () => {
        console.log('✅ SSE Connection established successfully');
        console.log('EventSource readyState after open:', eventSource.readyState);
        setConnectionStatus(prev => ({
          ...prev,
          status: 'connected',
          error: undefined,
          lastConnected: new Date().toISOString()
        }));
        setError(null);
        setRetryCount(0); // Reset retry count on successful connection
        
        // Start heartbeat timeout
        if (heartbeatTimeoutRef.current) {
          clearTimeout(heartbeatTimeoutRef.current);
        }
        heartbeatTimeoutRef.current = setTimeout(() => {
          console.warn('⚠️ No heartbeat received after connection');
          reconnectSSE();
        }, HEARTBEAT_TIMEOUT);
        
        // Fetch initial metrics when connection is established
        fetchInitialMetrics();
      };

      eventSource.onerror = (error) => {
        console.error('❌ SSE Connection error:', error);
        console.error('EventSource readyState:', eventSource.readyState);
        
        setConnectionStatus(prev => ({
          ...prev,
          status: 'error',
          error: 'Connection error'
        }));
        
        if (eventSource.readyState === EventSource.CLOSED) {
          console.log('🔄 Connection closed, attempting to reconnect...');
          eventSource.close();
          reconnectSSE();
        }
      };
    } catch (err) {
      console.error('❌ Error setting up SSE connection:', err);
      setError(err instanceof Error ? err : new Error('Failed to connect to SSE'));
      setConnectionStatus(prev => ({
        ...prev,
        status: 'error',
        error: err instanceof Error ? err.message : 'Unknown error'
      }));
      reconnectSSE();
    }
  }, [vcardId, retryCount, handleSSEEvent, reconnectSSE, navigate]);

  // Set up SSE connection on component mount
  useEffect(() => {
    console.log('🔄 Setting up SSE connection with VCard ID:', vcardId);
    connectSSE();
    
    // Clean up on unmount
    return () => {
      console.log('🧹 Cleaning up SSE connection');
      if (eventSourceRef.current) {
        console.log('🔌 Closing SSE connection on unmount');
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
  }, [vcardId, connectSSE]);

  // Expose a function to manually reconnect
  const reconnect = useCallback(() => {
    console.log('🔄 Manual reconnect requested');
    setRetryCount(0);
    connectSSE();
  }, [connectSSE]);

  return {
    metrics,
    error,
    isConnected: connectionStatus.status === 'connected',
    connectionStatus,
    reconnect
  };
};