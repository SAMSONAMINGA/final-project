/**
 * useWebSocket Hook
 * Manages WebSocket connection to /ws/live with auto-reconnect
 * Objective: Enable real-time county risk updates via Redis pub/sub
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { WebSocketEvent } from '@/types/floodguard';
import { api } from '@/lib/api';

interface UseWebSocketOptions {
  countiesCode?: string;
  onMessage: (event: WebSocketEvent) => void;
  onError?: (error: Event) => void;
  onConnect?: () => void;
  autoReconnect?: boolean;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}

export function useWebSocket({
  countiesCode,
  onMessage,
  onError,
  onConnect,
  autoReconnect = true,
  reconnectAttempts = 5,
  reconnectDelay = 3000,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const [isConnected, setIsConnected] = useState(false);

  const connect = useCallback(() => {
    if (wsRef.current) return;

    try {
      const socket = api.connectWebSocket(
        (event: WebSocketEvent) => {
          onMessage(event);
        },
        (error: Event) => {
          console.error('WebSocket error:', error);
          onError?.(error);
        },
        countiesCode,
      );

      socket.onopen = () => {
        setIsConnected(true);
        reconnectCountRef.current = 0;
        onConnect?.();
      };

      socket.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;

        if (autoReconnect && reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        }
      };
      wsRef.current = socket;
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      if (autoReconnect && reconnectCountRef.current < reconnectAttempts) {
        reconnectCountRef.current++;
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, reconnectDelay);
      }
    }
  }, [countiesCode, onMessage, onError, onConnect, autoReconnect, reconnectAttempts, reconnectDelay]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    send: (data: unknown) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(data));
      }
    },
  };
}
