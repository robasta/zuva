import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useWebSocket } from './WebSocketContext';
import { apiService } from '../services/apiService';

interface SystemStatus {
  timestamp: string;
  battery_soc: number;
  battery_power: number;
  solar_power: number;
  grid_power: number;
  load_power: number;
  battery_voltage: number;
  status: string;
}

interface MLPredictions {
  timestamp: string;
  battery_soc_1h: number;
  battery_soc_4h: number;
  battery_soc_24h: number;
  depletion_risk: number;
  charging_opportunity: number;
  confidence_score: number;
}

interface WeatherData {
  timestamp: string;
  correlation_score: number;
  cloud_impact: number;
  weather_trend: string;
  solar_forecast_1h: number;
  solar_forecast_4h: number;
  daily_total_kwh: number;
  forecast_confidence: number;
}

interface OptimizationPlan {
  timestamp: string;
  plan_confidence: number;
  solar_utilization_score: number;
  potential_daily_savings: number;
  recommendations: Array<{
    priority: string;
    action: string;
    reason: string;
    savings_potential: number;
    confidence: number;
  }>;
  device_schedules: Array<{
    device: string;
    optimal_time: string;
    reason: string;
    savings_potential: number;
  }>;
}

interface DataContextType {
  // Current data
  systemStatus: SystemStatus | null;
  mlPredictions: MLPredictions | null;
  weatherData: WeatherData | null;
  optimizationPlan: OptimizationPlan | null;
  
  // Historical data
  historicalData: any[];
  
  // Loading states
  isLoading: boolean;
  error: string | null;
  
  // Actions
  refreshData: () => Promise<void>;
  loadHistoricalData: (hours: number) => Promise<void>;
  clearError: () => void;
}

const DataContext = createContext<DataContextType | undefined>(undefined);

export const useData = (): DataContextType => {
  const context = useContext(DataContext);
  if (context === undefined) {
    throw new Error('useData must be used within a DataProvider');
  }
  return context;
};

interface DataProviderProps {
  children: ReactNode;
}

export const DataProvider: React.FC<DataProviderProps> = ({ children }) => {
  const { lastMessage, isConnected } = useWebSocket();
  
  // State
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [mlPredictions, setMlPredictions] = useState<MLPredictions | null>(null);
  const [weatherData, setWeatherData] = useState<WeatherData | null>(null);
  const [optimizationPlan, setOptimizationPlan] = useState<OptimizationPlan | null>(null);
  const [historicalData, setHistoricalData] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Handle WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      try {
        switch (lastMessage.type) {
          case 'system_status':
            setSystemStatus(lastMessage.data);
            break;
          case 'ml_predictions':
            setMlPredictions(lastMessage.data);
            break;
          case 'weather_update':
            setWeatherData(lastMessage.data);
            break;
          case 'optimization_update':
            setOptimizationPlan(lastMessage.data);
            break;
          case 'alert':
            // Handle alerts (could show notifications)
            console.log('Alert received:', lastMessage.data);
            break;
          default:
            console.log('Unknown message type:', lastMessage.type);
        }
      } catch (error) {
        console.error('Error processing WebSocket message:', error);
      }
    }
  }, [lastMessage]);

  // Initial data load
  useEffect(() => {
    if (isConnected) {
      refreshData();
    }
  }, [isConnected]);

  const refreshData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Load current data from API
      const [statusResponse, predictionsResponse, weatherResponse, optimizationResponse] = await Promise.allSettled([
        apiService.getCurrentData(),
        apiService.getMLPredictions(),
        apiService.getWeatherAnalysis(),
        apiService.getOptimizationPlan()
      ]);

      if (statusResponse.status === 'fulfilled' && statusResponse.value.success) {
        setSystemStatus(statusResponse.value.data);
      }

      if (predictionsResponse.status === 'fulfilled' && predictionsResponse.value.success) {
        setMlPredictions(predictionsResponse.value.data);
      }

      if (weatherResponse.status === 'fulfilled' && weatherResponse.value.success) {
        setWeatherData(weatherResponse.value.data);
      }

      if (optimizationResponse.status === 'fulfilled' && optimizationResponse.value.success) {
        setOptimizationPlan(optimizationResponse.value.data);
      }

      // Check for any errors
      const errors = [
        statusResponse.status === 'rejected' ? 'System status' : null,
        predictionsResponse.status === 'rejected' ? 'ML predictions' : null,
        weatherResponse.status === 'rejected' ? 'Weather data' : null,
        optimizationResponse.status === 'rejected' ? 'Optimization plan' : null
      ].filter(Boolean);

      if (errors.length > 0) {
        setError(`Failed to load: ${errors.join(', ')}`);
      }

    } catch (error) {
      console.error('Error refreshing data:', error);
      setError('Failed to refresh data');
    } finally {
      setIsLoading(false);
    }
  };

  const loadHistoricalData = async (hours: number = 24) => {
    setIsLoading(true);
    
    try {
      const response = await apiService.getHistoricalData(hours);
      if (response.success) {
        setHistoricalData(response.data.data || []);
      } else {
        setError('Failed to load historical data');
      }
    } catch (error) {
      console.error('Error loading historical data:', error);
      setError('Failed to load historical data');
    } finally {
      setIsLoading(false);
    }
  };

  const clearError = () => {
    setError(null);
  };

  const value: DataContextType = {
    systemStatus,
    mlPredictions,
    weatherData,
    optimizationPlan,
    historicalData,
    isLoading,
    error,
    refreshData,
    loadHistoricalData,
    clearError
  };

  return (
    <DataContext.Provider value={value}>
      {children}
    </DataContext.Provider>
  );
};
