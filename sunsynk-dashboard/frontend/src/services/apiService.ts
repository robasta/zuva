import axios, { AxiosResponse } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

class ApiService {
  private baseURL: string;
  private token: string | null = null;

  constructor() {
    this.baseURL = API_BASE_URL;
    
    // Setup axios defaults
    axios.defaults.timeout = 10000;
    
    // Add request interceptor to include auth token
    axios.interceptors.request.use(
      (config) => {
        const token = this.getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Add response interceptor for error handling
    axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          this.clearToken();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  private getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem('auth_token');
    }
    return this.token;
  }

  private clearToken(): void {
    this.token = null;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_expiry');
    localStorage.removeItem('auth_username');
  }

  public setToken(token: string): void {
    this.token = token;
  }

  private async request<T>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    endpoint: string,
    data?: any
  ): Promise<ApiResponse<T>> {
    try {
      const url = `${this.baseURL}${endpoint}`;
      
      let response: AxiosResponse<T>;
      
      switch (method) {
        case 'GET':
          response = await axios.get(url, { params: data });
          break;
        case 'POST':
          response = await axios.post(url, data);
          break;
        case 'PUT':
          response = await axios.put(url, data);
          break;
        case 'DELETE':
          response = await axios.delete(url);
          break;
        default:
          throw new Error(`Unsupported method: ${method}`);
      }

      return {
        success: true,
        data: response.data
      };
    } catch (error: any) {
      console.error(`API ${method} ${endpoint} error:`, error);
      
      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.message || 
                          error.message || 
                          'An unexpected error occurred';
      
      return {
        success: false,
        error: errorMessage
      };
    }
  }

  // Health check
  async healthCheck(): Promise<ApiResponse> {
    return this.request('GET', '/health');
  }

  // Authentication
  async login(username: string, password: string): Promise<ApiResponse> {
    return this.request('POST', '/auth/login', { username, password });
  }

  // Current data
  async getCurrentData(): Promise<ApiResponse> {
    return this.request('GET', '/dashboard/current');
  }

  // Historical data
  async getHistoricalData(hours: number = 24): Promise<ApiResponse> {
    return this.request('GET', '/dashboard/history', { hours });
  }

  // ML Analytics
  async getMLPredictions(): Promise<ApiResponse> {
    return this.request('GET', '/analytics/predictions');
  }

  // Weather analysis
  async getWeatherAnalysis(): Promise<ApiResponse> {
    return this.request('GET', '/analytics/weather');
  }

  // Optimization plan
  async getOptimizationPlan(): Promise<ApiResponse> {
    return this.request('GET', '/analytics/optimization');
  }

  // System configuration
  async getSystemConfig(): Promise<ApiResponse> {
    return this.request('GET', '/config');
  }

  async updateSystemConfig(config: any): Promise<ApiResponse> {
    return this.request('PUT', '/config', config);
  }

  // Alerts and notifications
  async getAlerts(): Promise<ApiResponse> {
    return this.request('GET', '/alerts');
  }

  async acknowledgeAlert(alertId: string): Promise<ApiResponse> {
    return this.request('POST', `/alerts/${alertId}/acknowledge`);
  }

  // Export data
  async exportData(format: 'csv' | 'json', startDate: string, endDate: string): Promise<ApiResponse> {
    return this.request('GET', '/export', { format, start_date: startDate, end_date: endDate });
  }
}

export const apiService = new ApiService();
export default apiService;
