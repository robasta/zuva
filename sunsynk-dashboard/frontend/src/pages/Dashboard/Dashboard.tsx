import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Card,
  CardContent,
  Box,
  CircularProgress,
  Alert,
  Chip,
  Paper,
  IconButton,
  Button,
  Typography
} from '@mui/material';
import {
  Battery80,
  WbSunny,
  SolarPower,
  ElectricalServices,
  Home,
  Refresh,
  CheckCircle,
  Error as ErrorIcon,
  TrendingUp,
  TrendingDown,
  Balance,
  CloudQueue,
  Thermostat,
  Air,
  Visibility
} from '@mui/icons-material';
import { formatTimeWithTimezone, formatDateTimeWithTimezone } from '../../utils/timezone';
import TimeSeriesGraph from '../../components/TimeSeriesGraph/TimeSeriesGraph';

const REFRESH_INTERVAL = 30000; // 30 seconds

interface DashboardMetrics {
  timestamp: string;
  solar_power: number;
  battery_level: number;
  grid_power: number;
  consumption: number;
  weather_condition: string;
  temperature: number;
}

interface SystemStatus {
  online: boolean;
  last_update: string;
  inverter_status: string;
  battery_status: string;
  grid_status: string;
}

interface WeatherForecast {
  time: string;
  temperature: number;
  condition: string;
  humidity: number;
  wind_speed: number;
  visibility: number;
}

interface DashboardData {
  metrics: DashboardMetrics;
  status: SystemStatus;
  weather_forecast?: WeatherForecast[];
}

export const Dashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [weatherForecast, setWeatherForecast] = useState<WeatherForecast[]>([]);
  const [lastUpdate, setLastUpdate] = useState<string>('');

  // Utility functions
  const formatPower = (power: number): string => {
    return `${power.toFixed(1)} kW`;
  };

  const formatPowerWithSign = (power: number): string => {
    return `${power > 0 ? '+' : ''}${power.toFixed(1)} kW`;
  };

  const fetchDashboardData = async () => {
    try {
      setError(null);
      
      // First authenticate
      const authResponse = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: 'admin',
          password: 'admin123'
        })
      });

      if (!authResponse.ok) {
        throw new Error('Authentication failed');
      }

      const authData = await authResponse.json();
      const token = authData.access_token;

      // Store token
      localStorage.setItem('auth_token', token);
      localStorage.setItem('auth_expiry', (Date.now() + 24 * 60 * 60 * 1000).toString());

      // Then fetch dashboard data
      const dashboardResponse = await fetch('/api/dashboard/current', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!dashboardResponse.ok) {
        throw new Error('Failed to fetch dashboard data');
      }

      const data = await dashboardResponse.json();
      setData(data);
      
      // Extract weather forecast from response
      if (data.weather_forecast && Array.isArray(data.weather_forecast)) {
        setWeatherForecast(data.weather_forecast);
      }
      
      setLastUpdate(formatTimeWithTimezone(new Date()));
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, []);

  const getGridStatusColor = (gridPower: number) => {
    if (gridPower > 0.1) return 'error'; // Importing
    if (gridPower < -0.1) return 'success'; // Exporting
    return 'warning'; // Independent
  };

  const getGridStatusText = (gridPower: number) => {
    if (gridPower > 0.1) return `Importing ${formatPowerWithSign(gridPower)}`;
    if (gridPower < -0.1) return `Exporting ${formatPowerWithSign(Math.abs(gridPower))}`;
    return 'Grid Independent';
  };

  const getBatteryIcon = (level: number) => {
    if (level > 75) return <Battery80 sx={{ color: '#4caf50' }} />;
    if (level > 25) return <Battery80 sx={{ color: '#ff9800' }} />;
    return <Battery80 sx={{ color: '#f44336' }} />;
  };

  const getEnergyBalance = (solarPower: number, consumption: number) => {
    return solarPower - consumption;
  };

  const getEnergyBalanceColor = (balance: number) => {
    if (balance > 1.0) return 'success';
    if (balance > 0.5) return 'success';
    if (balance > -0.5) return 'warning';
    if (balance > -1.5) return 'warning';
    return 'error';
  };

  const getEnergyBalanceIcon = (balance: number) => {
    if (balance > 0.5) return <TrendingUp sx={{ color: '#4caf50' }} />;
    if (balance > -0.5) return <Balance sx={{ color: '#ff9800' }} />;
    return <TrendingDown sx={{ color: '#f44336' }} />;
  };

  const getEnergyBalanceText = (balance: number) => {
    if (balance > 0.5) return `Surplus: ${formatPower(balance)}`;
    if (balance > -0.5) return 'Balanced';
    return `Deficit: ${formatPower(Math.abs(balance))}`;
  };

  const getEnergyBalanceDescription = (balance: number) => {
    if (balance > 1.5) return 'Excellent surplus';
    if (balance > 0.5) return 'Good surplus - charging battery';
    if (balance > -0.5) return 'Well balanced system';
    if (balance > -1.5) return 'Moderate deficit - using battery';
    return 'Large deficit - importing from grid';
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ ml: 2 }}>
          Loading Sunsynk Dashboard...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert 
        severity="error" 
        action={
          <Button color="inherit" size="small" onClick={fetchDashboardData}>
            Retry
          </Button>
        }
      >
        {error}
      </Alert>
    );
  }

  if (!data) {
    return (
      <Alert severity="warning">No dashboard data available</Alert>
    );
  }

  const { metrics, status } = data;

  return (
    <Container maxWidth="xl" sx={{ mt: 2, mb: 4 }}>
      <Grid container spacing={3}>
        {/* System Overview */}
        <Grid item xs={12}>
          <Paper sx={{ 
            p: 1.5, 
            mb: 2, 
            background: 'background.paper',
            color: 'text.primary',
            border: theme => `1px solid ${theme.palette.divider}`
          }}>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 500 }}>
                  Inverter: 2305156257 | Randburg, ZA | Last Update: {lastUpdate}
                </Typography>
              </Box>
              <Box display="flex" alignItems="center" gap={2}>
                <Chip 
                  icon={status.online ? <CheckCircle /> : <ErrorIcon />}
                  label={status.online ? 'Online' : 'Offline'}
                  color={status.online ? 'success' : 'error'}
                  sx={{ color: 'white' }}
                />
                <IconButton color="inherit" onClick={fetchDashboardData}>
                  <Refresh />
                </IconButton>
              </Box>
            </Box>
          </Paper>
        </Grid>

        {/* Power Generation */}
        <Grid item xs={12} md={6} lg={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <SolarPower sx={{ color: '#ff9800', mr: 1 }} />
                <Typography variant="h6">Solar Generation</Typography>
              </Box>
              <Typography variant="h3" component="div" color="primary">
                {formatPower(metrics.solar_power)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {metrics.temperature}°C | {metrics.weather_condition}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* House Consumption */}
        <Grid item xs={12} md={6} lg={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Home sx={{ color: '#9c27b0', mr: 1 }} />
                <Typography variant="h6">Consumption</Typography>
              </Box>
              <Typography variant="h3" component="div" color="primary">
                {formatPower(metrics.consumption)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                House Load
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Battery Status */}
        <Grid item xs={12} md={6} lg={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                {getBatteryIcon(metrics.battery_level)}
                <Typography variant="h6" sx={{ ml: 1 }}>Battery Status</Typography>
              </Box>
              <Typography variant="h3" component="div" color="primary">
                {metrics.battery_level.toFixed(1)}%
              </Typography>
              <Chip 
                label={status.battery_status}
                color={status.battery_status === 'normal' ? 'success' : 'warning'}
                size="small"
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Grid Power */}
        <Grid item xs={12} md={6} lg={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <ElectricalServices sx={{ color: '#4caf50', mr: 1 }} />
                <Typography variant="h6">Grid Power</Typography>
              </Box>
              <Typography variant="h3" component="div" color="primary">
                {formatPower(Math.abs(metrics.grid_power))}
              </Typography>
              <Chip 
                label={getGridStatusText(metrics.grid_power)}
                color={getGridStatusColor(metrics.grid_power)}
                size="small"
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Energy Balance */}
        <Grid item xs={12} md={6} lg={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                {getEnergyBalanceIcon(getEnergyBalance(metrics.solar_power, metrics.consumption))}
                <Typography variant="h6" sx={{ ml: 1 }}>Energy Balance</Typography>
              </Box>
              <Typography variant="h3" component="div" color="primary">
                {getEnergyBalanceText(getEnergyBalance(metrics.solar_power, metrics.consumption)).split(':')[0]}
              </Typography>
              <Typography variant="h6" component="div" color="primary" sx={{ mt: 1 }}>
                {getEnergyBalanceText(getEnergyBalance(metrics.solar_power, metrics.consumption)).includes(':') 
                  ? getEnergyBalanceText(getEnergyBalance(metrics.solar_power, metrics.consumption)).split(':')[1]?.trim()
                  : ''
                }
              </Typography>
              <Chip 
                label={getEnergyBalanceDescription(getEnergyBalance(metrics.solar_power, metrics.consumption))}
                color={getEnergyBalanceColor(getEnergyBalance(metrics.solar_power, metrics.consumption))}
                size="small"
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Time Series Graph */}
        <Grid item xs={12}>
          <TimeSeriesGraph 
            height={400}
            showControls={true}
            autoRefresh={true}
            refreshInterval={30000}
          />
        </Grid>

        {/* Smart Analytics */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                📊 Smart Analytics
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Typography variant="body1">Self-Consumption:</Typography>
                    <Typography variant="h6" color="primary">
                      {metrics.solar_power > 0 ? 
                        Math.min(100, (metrics.consumption / metrics.solar_power) * 100).toFixed(1) : 
                        '0.0'
                      }%
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12}>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Typography variant="body1">Grid Independence:</Typography>
                    <Chip 
                      label={Math.abs(metrics.grid_power) < 0.1 ? '✅ Yes' : '❌ No'}
                      color={Math.abs(metrics.grid_power) < 0.1 ? 'success' : 'error'}
                      size="small"
                    />
                  </Box>
                </Grid>
                <Grid item xs={12}>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="body1">System Efficiency:</Typography>
                    <Typography variant="h6" color="primary">95.2%</Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Weather Info */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <CloudQueue sx={{ color: '#2196f3', mr: 1 }} />
                <Typography variant="h6">Weather Forecast</Typography>
              </Box>
              {weatherForecast.length > 0 ? (
                <Box>
                  {/* Current Hour */}
                  <Box sx={{ mb: 2, p: 2, bgcolor: 'primary.light', borderRadius: 2 }}>
                    <Typography variant="subtitle2" color="primary.contrastText">Current Hour</Typography>
                    <Box display="flex" alignItems="center" gap={2}>
                      <Typography variant="h4" color="primary.contrastText">
                        {Math.round(weatherForecast[0]?.temperature || metrics.temperature)}°C
                      </Typography>
                      <Box>
                        <Typography variant="body2" color="primary.contrastText">
                          {weatherForecast[0]?.condition || metrics.weather_condition}
                        </Typography>
                        <Box display="flex" alignItems="center" gap={1}>
                          <Air sx={{ fontSize: 16, color: 'primary.contrastText' }} />
                          <Typography variant="caption" color="primary.contrastText">
                            {weatherForecast[0]?.wind_speed || 'N/A'} km/h
                          </Typography>
                          <Visibility sx={{ fontSize: 16, color: 'primary.contrastText', ml: 1 }} />
                          <Typography variant="caption" color="primary.contrastText">
                            {weatherForecast[0]?.visibility || 'N/A'} km
                          </Typography>
                        </Box>
                      </Box>
                    </Box>
                  </Box>
                  {/* Rest of Day Forecast */}
                  <Typography variant="subtitle2" gutterBottom>Rest of Day</Typography>
                  <Grid container spacing={1}>
                    {weatherForecast.slice(1, 7).map((forecast, index) => (
                      <Grid item xs={2} key={index}>
                        <Box textAlign="center" sx={{ p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
                          <Typography variant="caption" display="block">
                            {forecast.time}
                          </Typography>
                          <Typography variant="body2" fontWeight="bold">
                            {Math.round(forecast.temperature)}°
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {forecast.condition.split(' ')[0]}
                          </Typography>
                        </Box>
                      </Grid>
                    ))}
                  </Grid>
                </Box>
              ) : (
                <Box>
                  <Typography variant="h4" color="primary">
                    {metrics.temperature}°C
                  </Typography>
                  <Typography variant="body1" color="text.secondary">
                    {metrics.weather_condition}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Detailed forecast loading...
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
};

export default Dashboard;
