import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Box,
  Typography,
  Button,
  ButtonGroup,
  CircularProgress,
  Alert
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { apiService } from '../../services/apiService';

interface TimeSeriesDataPoint {
  timestamp: string;
  generation: number;
  consumption: number;
  battery_soc: number;
}

interface TimeSeriesProps {
  height?: number;
  showControls?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

type TimeRange = '6h' | '12h' | '24h';

const TimeSeriesGraph: React.FC<TimeSeriesProps> = ({
  height = 400,
  showControls = true,
  autoRefresh = true,
  refreshInterval = 900000  // 15 minutes instead of 30 seconds
}) => {
  const [data, setData] = useState<TimeSeriesDataPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');

  // Load data function
  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log(`Loading timeseries data for ${timeRange}...`);
      const response = await apiService.getTimeseriesData(`-${timeRange}`, '15m');
      
      console.log('Timeseries API response:', response);
      
      // Handle nested response structure: response.data.data contains the actual array
      const actualData = response.success && response.data && response.data.data ? response.data.data : [];
      
      if (response.success && Array.isArray(actualData) && actualData.length > 0) {
        console.log(`Received ${actualData.length} data points:`, actualData.slice(0, 2));

        const parseValue = (value: any): number | null => {
          if (value === null || value === undefined || value === '') {
            return null;
          }
          const numericValue = Number(value);
          return Number.isFinite(numericValue) ? numericValue : null;
        };

        const formattedData = actualData.reduce<TimeSeriesDataPoint[]>((acc, point: any) => {
          const parsedGeneration = parseValue(point.generation);
          const parsedConsumption = parseValue(point.consumption);
          const parsedBattery = parseValue(point.battery_soc ?? point.battery_level);

          const hasData =
            (parsedGeneration ?? 0) !== 0 ||
            (parsedConsumption ?? 0) !== 0 ||
            (parsedBattery ?? 0) !== 0;

          if (!hasData) {
            return acc;
          }

          acc.push({
            timestamp: point.timestamp,
            generation: parsedGeneration ?? 0,
            consumption: parsedConsumption ?? 0,
            battery_soc: parsedBattery ?? 0
          });
          return acc;
        }, []);

        // Debug consumption values
        const consumptionValues = formattedData.map(p => p.consumption);
        const consumptionRange = consumptionValues.length > 0 ? {
          min: Math.min(...consumptionValues),
          max: Math.max(...consumptionValues),
          avg: consumptionValues.reduce((a, b) => a + b, 0) / consumptionValues.length
        } : { min: 0, max: 0, avg: 0 };

        console.log('Raw data count:', actualData.length);
        console.log('Filtered data count:', formattedData.length);
        console.log('Formatted data sample:', formattedData.slice(0, 3));
        console.log('Consumption range:', consumptionRange);
        setData(formattedData);
      } else {
        console.error('API response not successful or no data:', {
          responseSuccess: response.success,
          hasData: !!response.data,
          dataType: typeof response.data,
          isArray: Array.isArray(response.data?.data),
          actualData: response.data?.data
        });
        setError(response.error || 'No data available');
      }
    } catch (err: any) {
      console.error('Failed to load timeseries data:', err);
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  // Load data on mount and when timeRange changes
  useEffect(() => {
    loadData();
  }, [timeRange]);

  // Auto refresh
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(loadData, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, timeRange]);

  return (
    <Card>
      <CardContent>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Box display="flex" alignItems="center">
            <TrendingUpIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant="h6">Energy Timeline</Typography>
          </Box>
          
          {showControls && (
            <Box display="flex" alignItems="center" gap={2}>
              <ButtonGroup size="small">
                <Button 
                  variant={timeRange === '6h' ? 'contained' : 'outlined'}
                  onClick={() => setTimeRange('6h')}
                >
                  6H
                </Button>
                <Button 
                  variant={timeRange === '12h' ? 'contained' : 'outlined'}
                  onClick={() => setTimeRange('12h')}
                >
                  12H
                </Button>
                <Button 
                  variant={timeRange === '24h' ? 'contained' : 'outlined'}
                  onClick={() => setTimeRange('24h')}
                >
                  24H
                </Button>
              </ButtonGroup>
              
              <Button
                size="small"
                startIcon={<RefreshIcon />}
                onClick={loadData}
                disabled={loading}
              >
                Refresh
              </Button>
            </Box>
          )}
        </Box>

        {/* Error State */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Debug Info */}
        {data.length > 0 && (
          <Box sx={{ mb: 2, p: 1, bgcolor: 'info.light', borderRadius: 1 }}>
            <Typography variant="caption" color="info.dark">
              Debug: {data.length} data points loaded for {timeRange}. 
              Sample: {data[0]?.timestamp} - Gen: {data[0]?.generation}kW, Cons: {data[0]?.consumption}kW, Batt: {data[0]?.battery_soc}%
            </Typography>
          </Box>
        )}

        {/* Chart */}
        <Box sx={{ width: '100%', height: height }}>
          {loading ? (
            <Box display="flex" justifyContent="center" alignItems="center" height="100%">
              <CircularProgress />
            </Box>
          ) : data.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="timestamp"
                  tickCount={6}
                  minTickGap={50}
                  tickFormatter={(value: string) => {
                    try {
                      const date = new Date(value);
                      return date.toLocaleTimeString('en-US', { 
                        hour: '2-digit', 
                        minute: '2-digit',
                        hour12: false 
                      });
                    } catch {
                      return '';
                    }
                  }}
                />
                <YAxis 
                  yAxisId="power"
                  orientation="left"
                  label={{ value: 'Power (kW)', angle: -90, position: 'insideLeft' }}
                />
                <YAxis 
                  yAxisId="battery"
                  orientation="right"
                  domain={[0, 100]}
                  label={{ value: 'Battery (%)', angle: 90, position: 'insideRight' }}
                />
                <Tooltip 
                  labelFormatter={(value: string) => {
                    try {
                      const date = new Date(value);
                      return date.toLocaleString();
                    } catch {
                      return value?.toString() || '';
                    }
                  }}
                  formatter={(value: any, _name: string, props: any) => {
                    const metricConfig: Record<string, { label: string; unit: string; precision: number }> = {
                      generation: { label: 'Solar Generation', unit: 'kW', precision: 2 },
                      consumption: { label: 'Consumption', unit: 'kW', precision: 2 },
                      battery_soc: { label: 'Battery SOC', unit: '%', precision: 1 }
                    };
                    const dataKey = String(props?.dataKey ?? '');
                    const metric = metricConfig[dataKey] ?? { label: dataKey, unit: '', precision: 2 };
                    const numericValue = Number(value ?? 0);
                    const safeValue = Number.isFinite(numericValue) ? numericValue : 0;
                    const formattedValue = metric.unit
                      ? `${safeValue.toFixed(metric.precision)} ${metric.unit}`
                      : safeValue.toFixed(metric.precision);
                    return [formattedValue, metric.label];
                  }}
                />
                <Legend 
                  verticalAlign="bottom" 
                  height={36}
                  iconType="circle"
                />
                <Line 
                  yAxisId="power"
                  type="monotone" 
                  dataKey="generation" 
                  stroke="transparent" 
                  strokeWidth={0}
                  name="Solar Generation"
                  dot={{ fill: "#ff9800", strokeWidth: 0, r: 4 }}
                  legendType="circle"
                />
                <Line 
                  yAxisId="power"
                  type="monotone" 
                  dataKey="consumption" 
                  stroke="transparent" 
                  strokeWidth={0}
                  name="Consumption"
                  dot={{ fill: "#9c27b0", strokeWidth: 0, r: 4 }}
                  legendType="circle"
                />
                <Line 
                  yAxisId="battery"
                  type="monotone" 
                  dataKey="battery_soc" 
                  stroke="transparent" 
                  strokeWidth={0}
                  name="Battery SOC"
                  dot={{ fill: "#4caf50", strokeWidth: 0, r: 4 }}
                  legendType="circle"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <Box 
              sx={{ 
                width: '100%', 
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexDirection: 'column',
                gap: 2,
                color: 'text.secondary'
              }}
            >
              <TrendingUpIcon sx={{ fontSize: 60 }} />
              <Typography variant="h6">
                No Data Available
              </Typography>
              <Typography variant="body2" textAlign="center">
                Unable to load timeseries data for the selected time range
              </Typography>
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default TimeSeriesGraph;
