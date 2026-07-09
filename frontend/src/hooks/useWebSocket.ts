import { useEffect, useRef, useCallback } from "react";

interface UseWebSocketOptions {
  onMessage: (data: any) => void;
  onError?: (e: Event) => void;
  reconnectDelay?: number;
}

export function useWebSocket(url: string, { onMessage, onError, reconnectDelay = 3000 }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const connect = useCallback(() => {
    if (typeof window === "undefined") return;
    // Allow passing a relative path like "/ws/market/AAPL" — derive ws(s) URL
    let resolved = url;
    if (url.startsWith("/")) {
      const scheme = window.location.protocol === "https:" ? "wss" : "ws";
      resolved = `${scheme}://${window.location.host}${url}`;
    } else if (typeof process !== "undefined" && process.env.NEXT_PUBLIC_WS_URL) {
      // If an explicit WS base is configured via env, use it.
      resolved = process.env.NEXT_PUBLIC_WS_URL.replace(/\/+$/g, "") + url;
    }

    const ws = new WebSocket(resolved);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)); } catch {}
    };

    ws.onerror = (e) => { onError?.(e); };

    ws.onclose = () => {
      reconnectTimer.current = setTimeout(connect, reconnectDelay);
    };
  }, [url, onMessage, onError, reconnectDelay]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { send };
}
