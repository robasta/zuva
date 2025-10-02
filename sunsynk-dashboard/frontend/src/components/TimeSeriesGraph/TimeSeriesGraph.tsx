import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  Box,
  Typography,
  Button,
  ButtonGroup,
  IconButton,
  TextField,
  Chip,
  CircularProgress,
  Alert,
  Tooltip,
  Grid
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  NavigateBefore as NavigateBeforeIcon,
  NavigateNext as NavigateNextIcon,
  Today as TodayIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { apiService } from '../../services/apiService';

interface TimeSeriesDataPoint {
  timestamp: string;
  generation: number;
  consumption: number;
  battery_soc: number;
  battery_level?: number;
}

interface TimeSeriesProps {
  height?: number;
  showControls?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

type TimeRange = '3h' | '6h' | '12h' | '24h';
type Resolution = '1m' | '5m' | '15m' | '1h';

const TIME_RANGE_OPTIONS: { value: TimeRange; label: string; resolution: Resolution }[] = [
  { value: '3h', label: '3 Hours', resolution: '1m' },
  { value: '6h', label: '6 Hours', resolution: '5m' },
  { value: '12h', label: '12 Hours', resolution: '5m' },
  { value: '24h', label: '24 Hours', resolution: '15m' }
];

const TimeSeriesGraph: React.FC<TimeSeriesProps> = ({
  height = 400,
  showControls = true,
  autoRefresh = true,
  refreshInterval = 30000
}) => {
  const [data, setData] = useState<TimeSeriesDataPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const [resolution, setResolution] = useState<Resolution>('15m');
  const [isToday, setIsToday] = useState(true);

  // Calculate start time based on selected date and time range
  const getStartTime = useCallback(() => {
    if (isToday) {
      // For today, use relative time
      return `-${timeRange}`;
    } else {
      // For historical dates, calculate absolute start time
      const selected = new Date(selectedDate);
      const hours = parseInt(timeRange.replace('h', ''));
      const startTime = new Date(selected.getTime() + (24 - hours) * 60 * 60 * 1000);
      return startTime.toISOString();
    }
  }, [selectedDate, timeRange, isToday]);

  // Load timeseries data
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const startTime = getStartTime();
      const response = await apiService.getTimeseriesData(startTime, resolution);
      
      if (response.success && response.data) {
        setData(response.data as TimeSeriesDataPoint[]);
      } else {
        throw new Error('Invalid response format');
      }
    } catch (err: any) {
      console.error('Failed to load timeseries data:', err);
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [getStartTime, resolution]);

  // Handle date navigation
  const navigateDate = (direction: 'prev' | 'next' | 'today') => {
    const current = new Date(selectedDate);
    
    switch (direction) {
      case 'prev':
        current.setDate(current.getDate() - 1);
        setSelectedDate(current.toISOString().split('T')[0]);
        setIsToday(false);
        break;
      case 'next':
        current.setDate(current.getDate() + 1);
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        if (current <= tomorrow) {
          setSelectedDate(current.toISOString().split('T')[0]);
          setIsToday(current.toDateString() === new Date().toDateString());
        }
        break;
      case 'today':
        setSelectedDate(new Date().toISOString().split('T')[0]);
        setIsToday(true);
        break;
    }
  };

  // Handle time range change
  const handleTimeRangeChange = (newRange: TimeRange) => {
    const option = TIME_RANGE_OPTIONS.find(opt => opt.value === newRange);
    if (option) {
      setTimeRange(newRange);
      setResolution(option.resolution);
    }
  };

  // Calculate summary statistics
  const getSummaryStats = () => {
    if (data.length === 0) return null;
    
    const avgGeneration = data.reduce((sum, point) => sum + point.generation, 0) / data.length;
    const avgConsumption = data.reduce((sum, point) => sum + point.consumption, 0) / data.length;
    const currentBattery = data[data.length - 1]?.battery_soc || 0;
    const maxGeneration = Math.max(...data.map(point => point.generation));
    const maxConsumption = Math.max(...data.map(point => point.consumption));
    
    return {
      avgGeneration,
      avgConsumption,
      currentBattery,
      maxGeneration,
      maxConsumption,
      totalDataPoints: data.length
    };
  };

  // Auto-refresh effect
  useEffect(() => {
    if (autoRefresh && isToday) {
      const interval = setInterval(loadData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, isToday, refreshInterval, loadData]);

  // Initial load and reload when dependencies change
  useEffect(() => {
    loadData();
  }, [loadData]);

  const stats = getSummaryStats();

  return (
    <Card sx={{ height: 'fit-content' }}>
      <CardHeader
        title={
          <Box display="flex" alignItems="center" gap={1}>
            <TrendingUpIcon color="primary" />
            <Typography variant="h6">Power & Battery Monitor</Typography>
            {loading && <CircularProgress size={20} />}
          </Box>
        }
        action={
          showControls && (
            <Box display="flex" alignItems="center" gap={1}>
              <Chip
                label={`${data.length} points`}
                size="small"
                variant="outlined"
              />
              <Tooltip title="Refresh">
                <IconButton onClick={loadData} disabled={loading}>
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
            </Box>
          )
        }
      />
      
      <CardContent>
        {showControls && (
          <Box sx={{ mb: 3 }}>
            {/* Date Navigation */}
            <Box display="flex" alignItems="center" gap={2} sx={{ mb: 2 }}>
              <Box display="flex" alignItems="center" gap={1}>
                <IconButton 
                  onClick={() => navigateDate('prev')}
                  size="small"
                >
                  <NavigateBeforeIcon />
                </IconButton>
                
                <TextField
                  type="date"
                  value={selectedDate}
                  onChange={(e) => {
                    setSelectedDate(e.target.value);
                    setIsToday(e.target.value === new Date().toISOString().split('T')[0]);
                  }}
                  size="small"
                  sx={{ width: 150 }}
                />
                
                <IconButton 
                  onClick={() => navigateDate('next')}
                  size="small"
                  disabled={selectedDate >= new Date().toISOString().split('T')[0]}
                >
                  <NavigateNextIcon />
                </IconButton>
                
                <Button
                  onClick={() => navigateDate('today')}
                  size="small"
                  startIcon={<TodayIcon />}
                  variant="outlined"
                >
                  Today
                </Button>
              </Box>

              {isToday && (
                <Chip
                  label="Live"
                  color="success"
                  size="small"
                  sx={{ animation: 'pulse 2s infinite' }}
                />
              )}
            </Box>

            {/* Time Range Controls */}
            <ButtonGroup size="small" variant="outlined">
              {TIME_RANGE_OPTIONS.map((option) => (
                <Button
                  key={option.value}
                  onClick={() => handleTimeRangeChange(option.value)}
                  variant={timeRange === option.value ? 'contained' : 'outlined'}
                >
                  {option.label}
                </Button>
              ))}
            </ButtonGroup>
          </Box>
        )}

        {/* Error Display */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Summary Statistics */}
        {stats && (
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={6} md={3}>
              <Box textAlign="center" p={2} bgcolor="primary.light" borderRadius={2}>
                <Typography variant="h4" color="primary.main">
                  {stats.avgGeneration.toFixed(1)}
                </Typography>
                <Typography variant="caption">Avg Generation (kW)</Typography>
              </Box>
            </Grid>
            <Grid item xs={6} md={3}>
              <Box textAlign="center" p={2} bgcolor="warning.light" borderRadius={2}>
                <Typography variant="h4" color="warning.main">
                  {stats.avgConsumption.toFixed(1)}
                </Typography>
                <Typography variant="caption">Avg Consumption (kW)</Typography>
              </Box>
            </Grid>
            <Grid item xs={6} md={3}>
              <Box textAlign="center" p={2} bgcolor="info.light" borderRadius={2}>
                <Typography variant="h4" color="info.main">
                  {stats.currentBattery.toFixed(1)}%
                </Typography>
                <Typography variant="caption">Current Battery SOC</Typography>
              </Box>
            </Grid>
            <Grid item xs={6} md={3}>
              <Box textAlign="center" p={2} bgcolor="success.light" borderRadius={2}>
                <Typography variant="h4" color="success.main">
                  {stats.maxGeneration.toFixed(1)}
                </Typography>
                <Typography variant="caption">Peak Generation (kW)</Typography>
              </Box>
            </Grid>
          </Grid>
        )}

        {/* Placeholder for Chart */}
        <Box 
          sx={{ 
            width: '100%', 
            height: height, 
            border: '2px dashed',
            borderColor: 'divider',
            borderRadius: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            gap: 2,
            bgcolor: 'background.default'
          }}
        >
          {loading ? (
            <CircularProgress size={60} />
          ) : (
            <>
              <TrendingUpIcon sx={{ fontSize: 60, color: 'text.disabled' }} />
              <Typography variant="h6" color="text.disabled">
                Time Series Chart
              </Typography>
              <Typography variant="body2" color="text.disabled" textAlign="center">
                Interactive chart with generation, consumption, and battery SOC data
              </Typography>
              {stats && (
                <Typography variant="caption" color="text.disabled">
                  Displaying {stats.totalDataPoints} data points for {timeRange}
                </Typography>
              )}
            </>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default TimeSeriesGraph;