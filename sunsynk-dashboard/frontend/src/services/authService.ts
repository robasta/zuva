import { apiService } from './apiService';

interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

interface AuthResponse {
  success: boolean;
  data?: LoginResponse;
  error?: string;
}

class AuthService {
  async login(username: string, password: string): Promise<AuthResponse> {
    try {
      const response = await apiService.login(username, password);
      
      if (response.success && response.data) {
        // Set the token in the API service
        apiService.setToken(response.data.access_token);
        
        return {
          success: true,
          data: response.data
        };
      } else {
        return {
          success: false,
          error: response.error || 'Login failed'
        };
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Login failed'
      };
    }
  }

  logout(): void {
    // Clear all authentication data
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_expiry');
    localStorage.removeItem('auth_username');
    
    // Clear token from API service
    apiService.setToken('');
  }

  isTokenValid(): boolean {
    const token = localStorage.getItem('auth_token');
    const expiry = localStorage.getItem('auth_expiry');
    
    if (!token || !expiry) {
      return false;
    }
    
    const expiryTime = parseInt(expiry, 10);
    return Date.now() < expiryTime;
  }

  getToken(): string | null {
    if (this.isTokenValid()) {
      return localStorage.getItem('auth_token');
    }
    return null;
  }

  getUsername(): string | null {
    if (this.isTokenValid()) {
      return localStorage.getItem('auth_username');
    }
    return null;
  }
}

export const authService = new AuthService();
export default authService;
