import React, { useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  LinearProgress,
  Paper,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Battery90 as BatteryIcon,
  WbSunny as SolarIcon,
  ElectricBolt as GridIcon,
  Home as LoadIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon
} from '@mui/icons-material';
import { useData } from '../../contexts/DataContext';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { formatPower } from '../../utils/powerUtils';

const Dashboard: React.FC = () => {
  const { systemStatus, mlPredictions, weatherData, optimizationPlan, isLoading, error, refreshData } = useData();
  const { isConnected, connectionStatus } = useWebSocket();

  useEffect(() => {
    // Load initial data
    refreshData();
  }, []);

  // Remove the old formatPower function as we're using the utility now

  const formatPercentage = (value: number): string => {
    if (!value && value !== 0) return '0%';
    return value.toFixed(1) + '%';
  };

  const getStatusColor = (value: number, type: string): string => {
    if (type === 'battery') {
      if (value >= 80) return '#28A745';
      if (value >= 50) return '#FFC107';
      if (value >= 20) return '#FF6B35';
      return '#DC3545';
    }
    if (type === 'solar') {
      if (value >= 4) return '#28A745';
      if (value >= 2) return '#FFC107';
      if (value >= 0.5) return '#FF6B35';
      return '#DC3545';
    }
    return '#2E8B57';
  };

  const MetricCard: React.FC<{
    title: string;
    value: string;
    icon: React.ReactNode;
    color: string;
    subtitle?: string;
    progress?: number;
  }> = ({ title, value, icon, color, subtitle, progress }) => (
    <Card sx={{ height: '100%', position: 'relative' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ color }}>{icon}</Box>
            <Typography variant="h6" component="h3" sx={{ fontWeight: 600 }}>
              {title}
            </Typography>
          </Box>
          {isConnected && (
            <Box sx={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#28A745' }} />
          )}
        </Box>
        
        <Typography variant="h4" component="div" sx={{ fontWeight: 700, color, mb: 1 }}>
          {value}
        </Typography>
        
        {subtitle && (
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            {subtitle}
          </Typography>
        )}
        
        {progress !== undefined && (
          <Box sx={{ mt: 2 }}>
            <LinearProgress
              variant="determinate"
              value={progress}
              sx={{
                height: 8,
                borderRadius: 4,
                backgroundColor: 'grey.200',
                '& .MuiLinearProgress-bar': {
                  backgroundColor: color,
                  borderRadius: 4,
                },
              }}
            />
          </Box>
        )}
      </CardContent>
    </Card>
  );

  const PredictionCard: React.FC = () => (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6" component="h3" sx={{ fontWeight: 600 }}>
            🤖 ML Predictions
          </Typography>
          {mlPredictions && (
            <Chip
              label={`${formatPercentage(mlPredictions.confidence_score * 100)} confidence`}
              size="small"
              color="primary"
              variant="outlined"
            />
          )}
        </Box>
        
        {mlPredictions ? (
          <Grid container spacing={2}>
            <Grid item xs={4}>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>1h forecast</Typography>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {formatPercentage(mlPredictions.battery_soc_1h)}
              </Typography>
            </Grid>
            <Grid item xs={4}>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>4h forecast</Typography>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {formatPercentage(mlPredictions.battery_soc_4h)}
              </Typography>
            </Grid>
            <Grid item xs={4}>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>24h forecast</Typography>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {formatPercentage(mlPredictions.battery_soc_24h)}
              </Typography>
            </Grid>
          </Grid>
        ) : (
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            Loading predictions...
          </Typography>
        )}
      </CardContent>
    </Card>
  );

  const WeatherCard: React.FC = () => (
    <Card>
      <CardContent>
        <Typography variant="h6" component="h3" sx={{ fontWeight: 600, mb: 2 }}>
          🌤️ Weather Analysis
        </Typography>
        
        {weatherData ? (
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>Correlation Score</Typography>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {weatherData.correlation_score.toFixed(2)}
              </Typography>
            </Box>
            
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>Weather Trend</Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {weatherData.weather_trend === 'improving' ? <TrendingUpIcon color="success" /> : <TrendingDownIcon color="error" />}
                <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                  {weatherData.weather_trend}
                </Typography>
              </Box>
            </Box>
            
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>Daily Forecast</Typography>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {weatherData.daily_total_kwh.toFixed(1)} kWh
              </Typography>
            </Box>
          </Box>
        ) : (
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            Loading weather data...
          </Typography>
        )}
      </CardContent>
    </Card>
  );

  const OptimizationCard: React.FC = () => (
    <Card>
      <CardContent>
        <Typography variant="h6" component="h3" sx={{ fontWeight: 600, mb: 2 }}>
          🎯 Optimization
        </Typography>
        
        {optimizationPlan ? (
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>Savings Potential</Typography>
              <Typography variant="h6" sx={{ fontWeight: 600, color: 'success.main' }}>
                {optimizationPlan.potential_daily_savings.toFixed(2)} kWh
              </Typography>
            </Box>
            
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>Solar Utilization</Typography>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {formatPercentage(optimizationPlan.solar_utilization_score)}
              </Typography>
            </Box>
            
            {optimizationPlan.recommendations.length > 0 && (
              <Box>
                <Typography variant="body2" sx={{ color: 'text.secondary', mb: 1 }}>Top Recommendation</Typography>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {optimizationPlan.recommendations[0].action}
                </Typography>
              </Box>
            )}
          </Box>
        ) : (
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            Loading optimization plan...
          </Typography>
        )}
      </CardContent>
    </Card>
  );

  if (error) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="error" gutterBottom>
          Error loading dashboard data
        </Typography>
        <Typography variant="body2" sx={{ mb: 2 }}>
          {error}
        </Typography>
        <IconButton onClick={refreshData} color="primary">
          <RefreshIcon />
        </IconButton>
      </Paper>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 600 }}>
          Dashboard
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Chip
            label={connectionStatus}
            color={isConnected ? 'success' : 'error'}
            size="small"
            variant="outlined"
          />
          
          <Tooltip title="Refresh Data">
            <IconButton onClick={refreshData} disabled={isLoading}>
              <RefreshIcon sx={{ animation: isLoading ? 'spin 1s linear infinite' : 'none' }} />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Main Metrics */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Battery"
            value={systemStatus ? formatPercentage(systemStatus.battery_soc) : 'Loading...'}
            icon={<BatteryIcon />}
            color={systemStatus ? getStatusColor(systemStatus.battery_soc, 'battery') : '#6C757D'}
            subtitle={systemStatus ? formatPower(systemStatus.battery_power) : ''}
            progress={systemStatus?.battery_soc}
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Solar Power"
            value={systemStatus ? formatPower(systemStatus.solar_power) : 'Loading...'}
            icon={<SolarIcon />}
            color={systemStatus ? getStatusColor(systemStatus.solar_power, 'solar') : '#FFA500'}
            subtitle="Current generation"
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Grid Power"
            value={systemStatus ? formatPower(systemStatus.grid_power) : 'Loading...'}
            icon={<GridIcon />}
            color={systemStatus?.grid_power !== undefined && systemStatus.grid_power > 0 ? '#DC3545' : '#28A745'}
            subtitle={systemStatus?.grid_power !== undefined && systemStatus.grid_power > 0 ? 'Importing' : 'Exporting'}
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Load Power"
            value={systemStatus ? formatPower(systemStatus.load_power) : 'Loading...'}
            icon={<LoadIcon />}
            color="#2E8B57"
            subtitle="Current consumption"
          />
        </Grid>
      </Grid>

      {/* Advanced Analytics */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <PredictionCard />
        </Grid>
        
        <Grid item xs={12} md={4}>
          <WeatherCard />
        </Grid>
        
        <Grid item xs={12} md={4}>
          <OptimizationCard />
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
