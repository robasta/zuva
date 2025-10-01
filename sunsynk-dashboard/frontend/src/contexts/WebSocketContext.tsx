import React, { createContext, useContext, ReactNode } from 'react';

// Simplified WebSocket context for non-router build
interface WebSocketContextType {
  isConnected: boolean;
  connectionStatus: string;
  lastMessage: any;
  sendMessage: (message: any) => void;
  subscribeToUpdates: (callback: (data: any) => void) => void;
  unsubscribeFromUpdates: (callback: (data: any) => void) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  // Stub implementation for simplified build
  const value: WebSocketContextType = {
    isConnected: false,
    connectionStatus: 'disconnected',
    lastMessage: null,
    sendMessage: () => {},
    subscribeToUpdates: () => {},
    unsubscribeFromUpdates: () => {},
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};
