import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authService } from '../services/authService';

interface User {
  username: string;
  token: string;
  expiresAt: number;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  refreshToken: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing token on mount
    const initializeAuth = async () => {
      try {
        const savedToken = localStorage.getItem('auth_token');
        const savedExpiry = localStorage.getItem('auth_expiry');
        const savedUsername = localStorage.getItem('auth_username');

        if (savedToken && savedExpiry && savedUsername) {
          const expiresAt = parseInt(savedExpiry, 10);
          
          if (Date.now() < expiresAt) {
            // Token is still valid
            setUser({
              username: savedUsername,
              token: savedToken,
              expiresAt
            });
          } else {
            // Token expired, clean up
            localStorage.removeItem('auth_token');
            localStorage.removeItem('auth_expiry');
            localStorage.removeItem('auth_username');
          }
        }
      } catch (error) {
        console.error('Error initializing auth:', error);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      setIsLoading(true);
      const response = await authService.login(username, password);
      
      if (response.success && response.data) {
        const expiresAt = Date.now() + (response.data.expires_in * 1000);
        
        const userData: User = {
          username,
          token: response.data.access_token,
          expiresAt
        };

        setUser(userData);
        
        // Save to localStorage
        localStorage.setItem('auth_token', response.data.access_token);
        localStorage.setItem('auth_expiry', expiresAt.toString());
        localStorage.setItem('auth_username', username);
        
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Login error:', error);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_expiry');
    localStorage.removeItem('auth_username');
  };

  const refreshToken = async (): Promise<boolean> => {
    if (!user) return false;
    
    try {
      // In a real implementation, you would call a refresh endpoint
      // For now, we'll just check if the current token is still valid
      if (Date.now() < user.expiresAt - 60000) { // 1 minute buffer
        return true;
      }
      
      // Token expired, logout
      logout();
      return false;
    } catch (error) {
      console.error('Token refresh error:', error);
      logout();
      return false;
    }
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    refreshToken
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
