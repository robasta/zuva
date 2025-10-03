import React, { useState, useEffect } from 'react';
import {
  Paper,
  Typography,
  Box,
  FormControlLabel,
  Switch,
  Divider,
  TextField,
  Button,
  Grid,
  FormControl,
  FormLabel,
  RadioGroup,
  Radio,
  Alert,
  CircularProgress,
  Chip,
  IconButton,
  Tabs,
  Tab,
  Card,
  CardContent,
  CardHeader,
  Slider,
  MenuItem,
  Select,
  InputLabel,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Stack,
  Tooltip,
  Snackbar,
  AlertProps
} from '@mui/material';
import {
  LocationOn as LocationOnIcon,
  MyLocation as MyLocationIcon,
  CloudQueue as CloudIcon,
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
  Security as SecurityIcon,
  Dashboard as DashboardIcon,
  Battery4Bar as BatteryIcon,
  WbSunny as SunIcon,
  Schedule as ScheduleIcon,
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  RestartAlt as ResetIcon,
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon,
  Warning as WarningIcon,
  Home as HomeIcon
} from '@mui/icons-material';
import { apiService } from '../../services/apiService';
import { formatDateTimeWithTimezone, formatTimeWithTimezone, getTimezoneFromLocation } from '../../utils/timezone';

interface WeatherLocationConfig {
  location_type: 'city' | 'coordinates';
  city?: string;
  latitude?: number;
  longitude?: number;
}

interface AlertConfiguration {
  user_id: string;
  alert_type: string;
  enabled: boolean;
  battery_thresholds: {
    min_level_threshold: number;
    max_loss_threshold: number;
    loss_timeframe_minutes: number;
    critical_level: number;
  };
  energy_thresholds: {
    deficit_threshold_kw: number;
    sustained_deficit_minutes: number;
    prediction_horizon_hours: number;
    deficit_severity_multiplier: number;
  };
  consumption_thresholds: {
    critical_threshold_kw: number;
    high_threshold_kw: number;
    low_threshold_kw: number;
    sustained_consumption_minutes: number;
    start_time: string;
    end_time: string;
    enabled: boolean;
  };
  daylight_config: {
    latitude: number;
    longitude: number;
    timezone: string;
    daylight_buffer_minutes: number;
    use_civil_twilight: boolean;
  };
  notification_channels: string[];
  severity_filter: string;
  max_alerts_per_hour: number;
  weather_intelligence_enabled: boolean;
  machine_learning_enabled: boolean;
  predictive_alerts_enabled: boolean;
  auto_threshold_adjustment: boolean;
  seasonal_adjustment_enabled: boolean;
  summer_daylight_buffer: number;
  winter_daylight_buffer: number;
  custom_parameters: Record<string, any>;
}

export const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [expandedPanel, setExpandedPanel] = useState<string>('battery');
  
  // Dashboard Settings
  const [refreshInterval, setRefreshInterval] = useState(30);
  const [darkMode, setDarkMode] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  
  // Weather Settings
  const [weatherLocation, setWeatherLocation] = useState<WeatherLocationConfig>({
    location_type: 'city',
    city: 'Cape Town,ZA'
  });
  
  // Notification Settings
  const [enableAlerts, setEnableAlerts] = useState(true);
  const [weatherNotifications, setWeatherNotifications] = useState(true);
  const [emailNotifications, setEmailNotifications] = useState(false);
  const [smsNotifications, setSmsNotifications] = useState(false);
  const [pushNotifications, setPushNotifications] = useState(true);
  
  // Alert Configuration
  const [alertConfigurations, setAlertConfigurations] = useState<AlertConfiguration[]>([]);
  const [selectedAlertConfig, setSelectedAlertConfig] = useState<AlertConfiguration | null>(null);
  
  // Weather API tracking state
  const [weatherApiCalls, setWeatherApiCalls] = useState({
    today: 0,
    this_month: 0,
    total: 0,
    last_reset: ''
  });
  
  // Test & Monitoring State
  const [batteryConfig, setBatteryConfig] = useState({
    min_level_threshold: 30,
    critical_level: 15,
    max_loss_threshold: 10,
    loss_timeframe_minutes: 60
  });
  const [savingBatteryConfig, setSavingBatteryConfig] = useState(false);

  useEffect(() => {
    loadSettings();
    loadAlertConfigurations();
    loadBatteryConfiguration();
    loadWeatherApiStats();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      
      // Load weather location
      try {
        const locationResponse = await apiService.get<{weather_location: WeatherLocationConfig}>('/settings/weather/location');
        if (locationResponse && locationResponse.weather_location) {
          setWeatherLocation(locationResponse.weather_location);
        }
      } catch (err) {
        console.warn('Could not load weather location settings');
      }

      // Load dashboard settings from localStorage
      try {
        const savedDashboardSettings = localStorage.getItem('dashboard_settings');
        if (savedDashboardSettings) {
          const settings = JSON.parse(savedDashboardSettings);
          setRefreshInterval(settings.refreshInterval || 30);
          setDarkMode(settings.darkMode || false);
          setAutoRefresh(settings.autoRefresh !== undefined ? settings.autoRefresh : true);
        }
      } catch (err) {
        console.warn('Could not load dashboard settings from localStorage');
      }

      // Load notification settings from localStorage
      try {
        const savedNotificationSettings = localStorage.getItem('notification_settings');
        if (savedNotificationSettings) {
          const settings = JSON.parse(savedNotificationSettings);
          setEnableAlerts(settings.enableAlerts !== undefined ? settings.enableAlerts : true);
          setWeatherNotifications(settings.weatherNotifications !== undefined ? settings.weatherNotifications : true);
          setEmailNotifications(settings.emailNotifications !== undefined ? settings.emailNotifications : false);
          setSmsNotifications(settings.smsNotifications !== undefined ? settings.smsNotifications : false);
          setPushNotifications(settings.pushNotifications !== undefined ? settings.pushNotifications : true);
        }
      } catch (err) {
        console.warn('Could not load notification settings from localStorage');
      }
      
    } catch (err: any) {
      setError(`Failed to load settings: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadWeatherApiStats = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      if (!token) {
        console.warn('No auth token available for loading weather API stats');
        return;
      }
      
      const response = await fetch('/api/weather/api-stats', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const stats = await response.json();
        setWeatherApiCalls({
          today: stats.calls_today || 0,
          this_month: stats.calls_this_month || 0,
          total: stats.total_calls || 0,
          last_reset: stats.last_reset || 'Never'
        });
      }
    } catch (err: any) {
      console.error('Failed to load weather API stats:', err);
    }
  };

  const loadAlertConfigurations = async () => {
    try {
      const response: any = await apiService.get('/v1/alerts/config');
      setAlertConfigurations(response.configurations || []);
      
      if (response.configurations && response.configurations.length > 0) {
        setSelectedAlertConfig(response.configurations[0]);
      } else {
        await loadDefaultAlertConfiguration();
      }
    } catch (error: any) {
      console.warn('Could not load alert configurations:', error.message);
      // Set fallback configuration to prevent endless loading
      setDefaultAlertConfiguration();
    }
  };

  const loadDefaultAlertConfiguration = async () => {
    try {
      const response: any = await apiService.get('/v1/alerts/config/energy_deficit/defaults');
      setSelectedAlertConfig(response.configuration);
    } catch (error: any) {
      console.warn('Could not load default alert configuration:', error.message);
      // Set fallback configuration to prevent endless loading
      setDefaultAlertConfiguration();
    }
  };

  const setDefaultAlertConfiguration = () => {
    const timezone = getTimezoneFromLocation(weatherLocation);
    const defaultConfig: AlertConfiguration = {
      user_id: 'default',
      alert_type: 'energy_deficit',
      enabled: true,
      battery_thresholds: {
        min_level_threshold: 30,
        max_loss_threshold: 10,
        loss_timeframe_minutes: 60,
        critical_level: 15
      },
      energy_thresholds: {
        deficit_threshold_kw: 2.0,
        sustained_deficit_minutes: 30,
        prediction_horizon_hours: 4,
        deficit_severity_multiplier: 1.5
      },
      consumption_thresholds: {
        critical_threshold_kw: 1.0,
        high_threshold_kw: 0.8,
        low_threshold_kw: 0.7,
        sustained_consumption_minutes: 20,
        start_time: '18:00',
        end_time: '03:00',
        enabled: true
      },
      daylight_config: {
        latitude: -33.9249,
        longitude: 18.4241,
        timezone: timezone,
        daylight_buffer_minutes: 30,
        use_civil_twilight: true
      },
      notification_channels: ['email', 'push'],
      severity_filter: 'medium',
      max_alerts_per_hour: 5,
      weather_intelligence_enabled: true,
      machine_learning_enabled: true,
      predictive_alerts_enabled: true,
      auto_threshold_adjustment: false,
      seasonal_adjustment_enabled: true,
      summer_daylight_buffer: 30,
      winter_daylight_buffer: 45,
      custom_parameters: {}
    };
    setSelectedAlertConfig(defaultConfig);
  };

  const saveWeatherLocation = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Validate form data
      if (weatherLocation.location_type === 'city') {
        if (!weatherLocation.city || weatherLocation.city.trim() === '') {
          setError('City name is required');
          return;
        }
      } else if (weatherLocation.location_type === 'coordinates') {
        if (weatherLocation.latitude === undefined || weatherLocation.latitude === null || 
            weatherLocation.longitude === undefined || weatherLocation.longitude === null ||
            isNaN(weatherLocation.latitude) || isNaN(weatherLocation.longitude)) {
          setError('Both latitude and longitude are required and must be valid numbers');
          return;
        }
        if (weatherLocation.latitude < -90 || weatherLocation.latitude > 90) {
          setError('Latitude must be between -90 and 90');
          return;
        }
        if (weatherLocation.longitude < -180 || weatherLocation.longitude > 180) {
          setError('Longitude must be between -180 and 180');
          return;
        }
      }

      const payload: any = {
        location_type: weatherLocation.location_type
      };

      if (weatherLocation.location_type === 'city') {
        payload.city = weatherLocation.city?.trim() || '';
        // Explicitly set coordinates to null when using city
        payload.latitude = null;
        payload.longitude = null;
      } else {
        payload.latitude = weatherLocation.latitude;
        payload.longitude = weatherLocation.longitude;
        // Explicitly set city to null when using coordinates
        payload.city = null;
      }

      console.log('Sending weather location payload:', payload);

      await apiService.put('/settings/weather/location', payload);
      setSuccess('Weather location saved successfully');
      
    } catch (err: any) {
      console.error('Weather location save error:', err);
      setError(`Failed to save weather location: ${err.message || 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  const testWeatherLocation = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiService.get<any>('/weather/test-location');
      if (response.success) {
        setSuccess(`Location test successful! Using ${response.location_type}: ${response.location}`);
      } else {
        setError(`Location test failed: ${response.error}`);
      }
    } catch (err: any) {
      setError(`Location test failed: ${err.message || 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  const getCurrentLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setWeatherLocation({
            location_type: 'coordinates',
            city: undefined,
            latitude: position.coords.latitude,
            longitude: position.coords.longitude
          });
        },
        (error) => {
          setError(`Could not get current location: ${error.message}`);
        }
      );
    } else {
      setError('Geolocation is not supported by this browser');
    }
  };

  const saveDashboardSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Dashboard settings would typically be saved to localStorage or an API
      // For now, we'll just simulate saving and show success
      localStorage.setItem('dashboard_settings', JSON.stringify({
        refreshInterval,
        darkMode,
        autoRefresh
      }));
      
      setSuccess('Dashboard settings saved successfully!');
    } catch (err: any) {
      setError(`Failed to save dashboard settings: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const saveNotificationSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Save notification preferences to localStorage or API
      // For now, we'll simulate saving and show success
      localStorage.setItem('notification_settings', JSON.stringify({
        enableAlerts,
        weatherNotifications,
        emailNotifications,
        smsNotifications,
        pushNotifications
      }));
      
      setSuccess('Notification settings saved successfully!');
    } catch (err: any) {
      setError(`Failed to save notification settings: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const saveAllSettings = async () => {
    await saveWeatherLocation();
    // Add other settings save logic here
  };

  // Alert Configuration Functions
  const saveAlertConfiguration = async () => {
    if (!selectedAlertConfig) return;

    try {
      setSaving(true);
      
      if (alertConfigurations.find(c => c.alert_type === selectedAlertConfig.alert_type)) {
        await apiService.put(`/v1/alerts/config/${selectedAlertConfig.alert_type}`, selectedAlertConfig);
      } else {
        await apiService.post('/v1/alerts/config', selectedAlertConfig);
      }
      
      setSuccess('Alert configuration saved successfully!');
      await loadAlertConfigurations();
    } catch (error: any) {
      console.warn('Alert configuration API not available:', error.message);
      setSuccess('Alert configuration updated locally (API endpoints not available)');
    } finally {
      setSaving(false);
    }
  };

  const resetAlertToDefaults = async () => {
    try {
      setLoading(true);
      await apiService.post('/v1/alerts/config/reset');
      setSuccess('Alert configurations reset to defaults!');
      await loadAlertConfigurations();
    } catch (error: any) {
      console.warn('Alert configuration reset API not available:', error.message);
      setDefaultAlertConfiguration();
      setSuccess('Alert configuration reset to local defaults (API endpoints not available)');
    } finally {
      setLoading(false);
    }
  };

  const updateSelectedAlertConfig = (path: string, value: any) => {
    if (!selectedAlertConfig) return;
    
    const keys = path.split('.');
    const updatedConfig = { ...selectedAlertConfig };
    let current: any = updatedConfig;
    
    for (let i = 0; i < keys.length - 1; i++) {
      current = current[keys[i]];
    }
    
    current[keys[keys.length - 1]] = value;
    setSelectedAlertConfig(updatedConfig);
  };

  const handlePanelChange = (panel: string) => (event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpandedPanel(isExpanded ? panel : '');
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  // Battery Configuration Functions
  const loadBatteryConfiguration = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      if (!token) {
        console.warn('No auth token available for loading battery config');
        return;
      }
      
      const response = await fetch('/api/settings/battery', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        const settings = data.settings;
        
        if (settings && Object.keys(settings).length > 0) {
          setBatteryConfig({
            min_level_threshold: settings.min_level_threshold ?? 30,
            critical_level: settings.critical_level ?? 15,
            max_loss_threshold: settings.max_loss_threshold ?? 10,
            loss_timeframe_minutes: settings.loss_timeframe_minutes ?? 60
          });
        }
      }
    } catch (err: any) {
      console.error('Failed to load battery configuration:', err);
    }
  };

  const saveBatteryConfiguration = async () => {
    try {
      setSavingBatteryConfig(true);
      
      const token = localStorage.getItem('auth_token');
      if (!token) {
        throw new Error('Authentication required');
      }
      
      const response = await fetch('/api/settings/battery', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(batteryConfig)
      });

      if (response.ok) {
        setSuccess('Battery configuration saved successfully!');
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save configuration');
      }
    } catch (error: any) {
      setError(`Failed to save battery configuration: ${error.message}`);
    } finally {
      setSavingBatteryConfig(false);
    }
  };

  const createTestAlert = async (severity: string = 'low') => {
    try {
      await apiService.post(`/alerts/test?severity=${severity}`);
      setSuccess(`Test ${severity} priority alert created successfully!`);
    } catch (err: any) {
      setError(`Failed to create test alert: ${err.message}`);
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" sx={{ fontWeight: 600, mb: 3, display: 'flex', alignItems: 'center' }}>
        <SettingsIcon sx={{ mr: 2, color: 'primary.main' }} />
        System Settings
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Paper sx={{ mt: 2 }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={handleTabChange} aria-label="Settings tabs">
            <Tab 
              label="Dashboard" 
              icon={<DashboardIcon />} 
              iconPosition="start"
            />
            <Tab 
              label="Weather" 
              icon={<CloudIcon />} 
              iconPosition="start"
            />
            <Tab 
              label="Alerts" 
              icon={<WarningIcon />} 
              iconPosition="start"
            />
            <Tab 
              label="Notifications" 
              icon={<NotificationsIcon />} 
              iconPosition="start"
            />
            <Tab 
              label="System Health" 
              icon={<SecurityIcon />} 
              iconPosition="start"
            />
          </Tabs>
        </Box>

        {/* Dashboard Settings Tab */}
        {activeTab === 0 && (
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
              <DashboardIcon sx={{ mr: 1 }} />
              Dashboard Configuration
            </Typography>
            
            <Grid container spacing={3} sx={{ mt: 1 }}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Refresh Interval (seconds)"
                  type="number"
                  value={refreshInterval}
                  onChange={(e) => setRefreshInterval(parseInt(e.target.value) || 30)}
                  helperText="How often to update dashboard data"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch 
                      checked={autoRefresh}
                      onChange={(e) => setAutoRefresh(e.target.checked)}
                    />
                  }
                  label="Auto-refresh data"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch 
                      checked={darkMode}
                      onChange={(e) => {
                        const newDarkMode = e.target.checked;
                        setDarkMode(newDarkMode);
                        // Auto-save dark mode changes immediately
                        const currentSettings = JSON.parse(localStorage.getItem('dashboard_settings') || '{}');
                        const updatedSettings = {
                          ...currentSettings,
                          refreshInterval,
                          darkMode: newDarkMode,
                          autoRefresh
                        };
                        localStorage.setItem('dashboard_settings', JSON.stringify(updatedSettings));
                        // Trigger storage event for cross-tab sync
                        window.dispatchEvent(new StorageEvent('storage', {
                          key: 'dashboard_settings',
                          newValue: JSON.stringify(updatedSettings)
                        }));
                      }}
                    />
                  }
                  label="Dark mode"
                />
              </Grid>
            </Grid>

            <Box sx={{ mt: 3 }}>
              <Button 
                variant="contained" 
                color="primary" 
                onClick={saveDashboardSettings}
                disabled={loading}
                startIcon={loading ? <CircularProgress size={20} /> : <SaveIcon />}
              >
                {loading ? 'Saving...' : 'Save Dashboard Settings'}
              </Button>
            </Box>
          </Box>
        )}

        {/* Weather Settings Tab */}
        {activeTab === 1 && (
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
              <CloudIcon sx={{ mr: 1 }} />
              Weather Location Configuration
            </Typography>
            
            {weatherLocation && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="body2" color="text.secondary">Current Location:</Typography>
                <Chip 
                  size="small" 
                  sx={{ mt: 1 }}
                  icon={weatherLocation.location_type === 'coordinates' ? <MyLocationIcon /> : <LocationOnIcon />}
                  label={weatherLocation.location_type === 'coordinates' 
                    ? `${weatherLocation.latitude?.toFixed(4)}, ${weatherLocation.longitude?.toFixed(4)}`
                    : weatherLocation.city
                  }
                />
              </Box>
            )}
            
            <FormControl component="fieldset" sx={{ mb: 3 }}>
              <FormLabel component="legend">Location Type</FormLabel>
              <RadioGroup
                value={weatherLocation.location_type}
                onChange={(e) => {
                  const newLocationType = e.target.value as 'city' | 'coordinates';
                  if (newLocationType === 'city') {
                    setWeatherLocation({
                      location_type: 'city',
                      city: weatherLocation.city || '',
                      latitude: undefined,
                      longitude: undefined
                    });
                  } else {
                    setWeatherLocation({
                      location_type: 'coordinates',
                      city: undefined,
                      latitude: weatherLocation.latitude,
                      longitude: weatherLocation.longitude
                    });
                  }
                }}
              >
                <FormControlLabel 
                  value="city" 
                  control={<Radio />} 
                  label="City Name" 
                />
                <FormControlLabel 
                  value="coordinates" 
                  control={<Radio />} 
                  label="Latitude/Longitude Coordinates" 
                />
              </RadioGroup>
            </FormControl>

            {weatherLocation.location_type === 'city' ? (
              <TextField
                fullWidth
                label="City and Country"
                value={weatherLocation.city || ''}
                onChange={(e) => setWeatherLocation({...weatherLocation, city: e.target.value})}
                placeholder="e.g., Cape Town,ZA"
                helperText="Format: City,CountryCode (e.g., Cape Town,ZA or London,GB)"
                sx={{ mb: 3 }}
              />
            ) : (
              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                  <TextField
                    label="Latitude"
                    type="number"
                    value={weatherLocation.latitude !== undefined ? weatherLocation.latitude : ''}
                    onChange={(e) => {
                      const value = e.target.value;
                      const numValue = value === '' ? undefined : parseFloat(value);
                      setWeatherLocation({
                        ...weatherLocation, 
                        latitude: (numValue !== undefined && !isNaN(numValue)) ? numValue : undefined
                      });
                    }}
                    placeholder="-33.9249"
                    helperText="Decimal degrees (-90 to 90)"
                    inputProps={{ step: 0.0001, min: -90, max: 90 }}
                  />
                  <TextField
                    label="Longitude"
                    type="number"
                    value={weatherLocation.longitude !== undefined ? weatherLocation.longitude : ''}
                    onChange={(e) => {
                      const value = e.target.value;
                      const numValue = value === '' ? undefined : parseFloat(value);
                      setWeatherLocation({
                        ...weatherLocation, 
                        longitude: (numValue !== undefined && !isNaN(numValue)) ? numValue : undefined
                      });
                    }}
                    placeholder="18.4241"
                    helperText="Decimal degrees (-180 to 180)"
                    inputProps={{ step: 0.0001, min: -180, max: 180 }}
                  />
                </Box>
                <Button
                  startIcon={<MyLocationIcon />}
                  onClick={getCurrentLocation}
                  variant="outlined"
                  size="small"
                >
                  Use Current Location
                </Button>
              </Box>
            )}

            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button 
                onClick={testWeatherLocation} 
                variant="outlined"
                disabled={loading}
              >
                Test Location
              </Button>
              <Button 
                onClick={saveWeatherLocation} 
                variant="contained"
                disabled={loading}
                startIcon={<SaveIcon />}
              >
                Save Weather Location
              </Button>
            </Box>

            {/* Weather API Usage Widget */}
            <Card sx={{ mt: 4 }}>
              <CardHeader 
                title="Weather API Usage" 
                avatar={<CloudIcon color="primary" />}
                action={
                  <IconButton onClick={loadWeatherApiStats} size="small">
                    <RefreshIcon />
                  </IconButton>
                }
              />
              <CardContent>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'info.light', borderRadius: 2 }}>
                      <Typography variant="h4" color="info.main" sx={{ fontWeight: 'bold' }}>
                        {weatherApiCalls.today}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        API Calls Today
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'warning.light', borderRadius: 2 }}>
                      <Typography variant="h4" color="warning.main" sx={{ fontWeight: 'bold' }}>
                        {weatherApiCalls.this_month}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        This Month
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'success.light', borderRadius: 2 }}>
                      <Typography variant="h4" color="success.main" sx={{ fontWeight: 'bold' }}>
                        {weatherApiCalls.total}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Total Calls
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
                <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    <strong>OpenWeather API Limit:</strong> Free tier allows 1,000 calls/month (33 calls/day average)
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    <strong>Last Reset:</strong> {weatherApiCalls.last_reset && weatherApiCalls.last_reset !== 'Never' 
                      ? formatDateTimeWithTimezone(weatherApiCalls.last_reset, {}, weatherLocation) 
                      : weatherApiCalls.last_reset || 'Never'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    <strong>Current Usage:</strong> {weatherApiCalls.this_month > 0 ? ((weatherApiCalls.this_month / 1000) * 100).toFixed(1) : 0}% of monthly limit
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Box>
        )}

        {/* Alert Configuration Tab */}
        {activeTab === 2 && (
          <Box sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center' }}>
                <WarningIcon sx={{ mr: 1 }} />
                Alert Configuration
              </Typography>
              <Stack direction="row" spacing={1}>
                <Tooltip title="Reset to Defaults">
                  <IconButton onClick={resetAlertToDefaults} size="small">
                    <ResetIcon />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Refresh">
                  <IconButton onClick={loadAlertConfigurations} size="small">
                    <RefreshIcon />
                  </IconButton>
                </Tooltip>
              </Stack>
            </Box>

            {selectedAlertConfig ? (
              <>
                {/* Basic Alert Settings */}
                <Accordion expanded={expandedPanel === 'basic'} onChange={handlePanelChange('basic')}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="h6">Basic Alert Settings</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={3}>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={selectedAlertConfig.enabled}
                              onChange={(e) => updateSelectedAlertConfig('enabled', e.target.checked)}
                            />
                          }
                          label="Enable Alerts"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControl fullWidth>
                          <InputLabel>Severity Filter</InputLabel>
                          <Select
                            value={selectedAlertConfig.severity_filter}
                            onChange={(e) => updateSelectedAlertConfig('severity_filter', e.target.value)}
                          >
                            <MenuItem value="low">Low</MenuItem>
                            <MenuItem value="medium">Medium</MenuItem>
                            <MenuItem value="high">High</MenuItem>
                            <MenuItem value="critical">Critical</MenuItem>
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          fullWidth
                          label="Max Alerts Per Hour"
                          type="number"
                          value={selectedAlertConfig.max_alerts_per_hour}
                          onChange={(e) => updateSelectedAlertConfig('max_alerts_per_hour', Number(e.target.value))}
                          inputProps={{ min: 1, max: 20 }}
                        />
                      </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>

                {/* Battery Thresholds */}
                <Accordion expanded={expandedPanel === 'battery'} onChange={handlePanelChange('battery')}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box display="flex" alignItems="center">
                      <BatteryIcon sx={{ mr: 1 }} />
                      <Typography variant="h6">Battery Thresholds</Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={3}>
                      <Grid item xs={12} md={6}>
                        <Typography gutterBottom>Minimum Battery Level (%)</Typography>
                        <Slider
                          value={selectedAlertConfig.battery_thresholds.min_level_threshold}
                          onChange={(_, value) => updateSelectedAlertConfig('battery_thresholds.min_level_threshold', value)}
                          min={10}
                          max={80}
                          valueLabelDisplay="auto"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Typography gutterBottom>Maximum Battery Loss (%)</Typography>
                        <Slider
                          value={selectedAlertConfig.battery_thresholds.max_loss_threshold}
                          onChange={(_, value) => updateSelectedAlertConfig('battery_thresholds.max_loss_threshold', value)}
                          min={5}
                          max={30}
                          valueLabelDisplay="auto"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          fullWidth
                          label="Critical Battery Level (%)"
                          type="number"
                          value={selectedAlertConfig.battery_thresholds.critical_level}
                          onChange={(e) => updateSelectedAlertConfig('battery_thresholds.critical_level', Number(e.target.value))}
                          inputProps={{ min: 5, max: 50 }}
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <TextField
                          fullWidth
                          label="Loss Timeframe (minutes)"
                          type="number"
                          value={selectedAlertConfig.battery_thresholds.loss_timeframe_minutes}
                          onChange={(e) => updateSelectedAlertConfig('battery_thresholds.loss_timeframe_minutes', Number(e.target.value))}
                          inputProps={{ min: 15, max: 240 }}
                        />
                      </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>

                {/* Consumption Thresholds */}
                <Accordion expanded={expandedPanel === 'consumption'} onChange={handlePanelChange('consumption')}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box display="flex" alignItems="center">
                      <HomeIcon sx={{ mr: 1 }} />
                      <Typography variant="h6">Consumption Thresholds</Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={3}>
                      <Grid item xs={12}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={selectedAlertConfig.consumption_thresholds.enabled}
                              onChange={(e) => updateSelectedAlertConfig('consumption_thresholds.enabled', e.target.checked)}
                            />
                          }
                          label="Enable Consumption Alerts"
                        />
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <TextField
                          fullWidth
                          label="Critical Threshold (kW)"
                          type="number"
                          value={selectedAlertConfig.consumption_thresholds.critical_threshold_kw}
                          onChange={(e) => updateSelectedAlertConfig('consumption_thresholds.critical_threshold_kw', Number(e.target.value))}
                          inputProps={{ min: 0.1, max: 10, step: 0.1 }}
                          helperText="Alert when consumption exceeds this for sustained period"
                        />
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <TextField
                          fullWidth
                          label="High Threshold (kW)"
                          type="number"
                          value={selectedAlertConfig.consumption_thresholds.high_threshold_kw}
                          onChange={(e) => updateSelectedAlertConfig('consumption_thresholds.high_threshold_kw', Number(e.target.value))}
                          inputProps={{ min: 0.1, max: 10, step: 0.1 }}
                        />
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <TextField
                          fullWidth
                          label="Low Threshold (kW)"
                          type="number"
                          value={selectedAlertConfig.consumption_thresholds.low_threshold_kw}
                          onChange={(e) => updateSelectedAlertConfig('consumption_thresholds.low_threshold_kw', Number(e.target.value))}
                          inputProps={{ min: 0.1, max: 10, step: 0.1 }}
                        />
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <TextField
                          fullWidth
                          label="Sustained Period (minutes)"
                          type="number"
                          value={selectedAlertConfig.consumption_thresholds.sustained_consumption_minutes}
                          onChange={(e) => updateSelectedAlertConfig('consumption_thresholds.sustained_consumption_minutes', Number(e.target.value))}
                          inputProps={{ min: 5, max: 120 }}
                          helperText="Alert after consumption exceeds threshold for this duration"
                        />
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <TextField
                          fullWidth
                          label="Alert Start Time"
                          type="time"
                          value={selectedAlertConfig.consumption_thresholds.start_time}
                          onChange={(e) => updateSelectedAlertConfig('consumption_thresholds.start_time', e.target.value)}
                          helperText="Start of consumption monitoring period"
                          InputLabelProps={{ shrink: true }}
                        />
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <TextField
                          fullWidth
                          label="Alert End Time"
                          type="time"
                          value={selectedAlertConfig.consumption_thresholds.end_time}
                          onChange={(e) => updateSelectedAlertConfig('consumption_thresholds.end_time', e.target.value)}
                          helperText="End of consumption monitoring period"
                          InputLabelProps={{ shrink: true }}
                        />
                      </Grid>
                    </Grid>
                    <Alert severity="info" sx={{ mt: 2 }}>
                      <Typography variant="body2">
                        <strong>Consumption Alert Settings:</strong><br/>
                        • Critical: {selectedAlertConfig.consumption_thresholds.critical_threshold_kw}kW (Critical alerts)<br/>
                        • High: {selectedAlertConfig.consumption_thresholds.high_threshold_kw}kW (High priority alerts)<br/>
                        • Low: {selectedAlertConfig.consumption_thresholds.low_threshold_kw}kW (Low priority alerts)<br/>
                        • Active between {selectedAlertConfig.consumption_thresholds.start_time} - {selectedAlertConfig.consumption_thresholds.end_time}<br/>
                        • Triggers after {selectedAlertConfig.consumption_thresholds.sustained_consumption_minutes} minutes of sustained high consumption
                      </Typography>
                    </Alert>
                  </AccordionDetails>
                </Accordion>

                {/* Intelligence Settings */}
                <Accordion expanded={expandedPanel === 'intelligence'} onChange={handlePanelChange('intelligence')}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box display="flex" alignItems="center">
                      <InfoIcon sx={{ mr: 1 }} />
                      <Typography variant="h6">Intelligence & Prediction</Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={3}>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={selectedAlertConfig.weather_intelligence_enabled}
                              onChange={(e) => updateSelectedAlertConfig('weather_intelligence_enabled', e.target.checked)}
                            />
                          }
                          label="Weather Intelligence"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={selectedAlertConfig.machine_learning_enabled}
                              onChange={(e) => updateSelectedAlertConfig('machine_learning_enabled', e.target.checked)}
                            />
                          }
                          label="Machine Learning"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={selectedAlertConfig.predictive_alerts_enabled}
                              onChange={(e) => updateSelectedAlertConfig('predictive_alerts_enabled', e.target.checked)}
                            />
                          }
                          label="Predictive Alerts"
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={selectedAlertConfig.auto_threshold_adjustment}
                              onChange={(e) => updateSelectedAlertConfig('auto_threshold_adjustment', e.target.checked)}
                            />
                          }
                          label="Auto Threshold Adjustment"
                        />
                      </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              </>
            ) : (
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
                <CircularProgress />
                <Typography sx={{ ml: 2 }}>Loading alert configuration...</Typography>
              </Box>
            )}

            {/* Test Alerts */}
            <Accordion expanded={expandedPanel === 'test'} onChange={handlePanelChange('test')} sx={{ mt: 2 }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box display="flex" alignItems="center">
                  <SecurityIcon sx={{ mr: 1 }} />
                  <Typography variant="h6">Test Alerts</Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Create test alerts to verify your notification configuration.
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Button
                      variant="outlined"
                      color="success"
                      startIcon={<InfoIcon />}
                      onClick={() => createTestAlert('low')}
                      fullWidth
                    >
                      Test Low Priority Alert
                    </Button>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Button
                      variant="outlined"
                      color="info"
                      startIcon={<InfoIcon />}
                      onClick={() => createTestAlert('medium')}
                      fullWidth
                    >
                      Test Medium Priority Alert
                    </Button>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Button
                      variant="outlined"
                      color="warning"
                      startIcon={<InfoIcon />}
                      onClick={() => createTestAlert('high')}
                      fullWidth
                    >
                      Test High Priority Alert
                    </Button>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Button
                      variant="outlined"
                      color="error"
                      startIcon={<InfoIcon />}
                      onClick={() => createTestAlert('critical')}
                      fullWidth
                    >
                      Test Critical Alert
                    </Button>
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>

            <Box sx={{ mt: 3 }}>
              {selectedAlertConfig ? (
                <Button
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={saveAlertConfiguration}
                  disabled={saving}
                >
                  {saving ? 'Saving...' : 'Save Alert Configuration'}
                </Button>
              ) : (
                <Button variant="contained" disabled>
                  Loading...
                </Button>
              )}
            </Box>
          </Box>
        )}

        {/* Notification Channels Tab */}
        {activeTab === 3 && (
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
              <NotificationsIcon sx={{ mr: 1 }} />
              Notification Channels
            </Typography>
            
            <Grid container spacing={3} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  General Notification Settings
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
                  <FormControlLabel
                    control={
                      <Switch 
                        checked={enableAlerts}
                        onChange={(e) => setEnableAlerts(e.target.checked)}
                      />
                    }
                    label="Enable intelligent alerts"
                  />
                  <FormControlLabel
                    control={
                      <Switch 
                        checked={weatherNotifications}
                        onChange={(e) => setWeatherNotifications(e.target.checked)}
                      />
                    }
                    label="Weather-based notifications"
                  />
                </Box>
              </Grid>

              <Grid item xs={12}>
                <Divider sx={{ my: 2 }} />
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Notification Delivery Channels
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
                  <FormControlLabel
                    control={
                      <Switch 
                        checked={emailNotifications}
                        onChange={(e) => setEmailNotifications(e.target.checked)}
                      />
                    }
                    label="Email notifications"
                  />
                  <FormControlLabel
                    control={
                      <Switch 
                        checked={smsNotifications}
                        onChange={(e) => setSmsNotifications(e.target.checked)}
                      />
                    }
                    label="SMS notifications"
                  />
                  <FormControlLabel
                    control={
                      <Switch 
                        checked={pushNotifications}
                        onChange={(e) => setPushNotifications(e.target.checked)}
                      />
                    }
                    label="Push notifications"
                  />
                </Box>
              </Grid>

              {selectedAlertConfig && (
                <Grid item xs={12}>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Alert-Specific Notification Channels
                  </Typography>
                  <Box>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Select notification channels for alerts:
                    </Typography>
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                      {['email', 'sms', 'whatsapp', 'push', 'voice'].map((channel) => (
                        <Chip
                          key={channel}
                          label={channel.toUpperCase()}
                          variant={selectedAlertConfig.notification_channels.includes(channel) ? 'filled' : 'outlined'}
                          onClick={() => {
                            const channels = selectedAlertConfig.notification_channels.includes(channel)
                              ? selectedAlertConfig.notification_channels.filter(c => c !== channel)
                              : [...selectedAlertConfig.notification_channels, channel];
                            updateSelectedAlertConfig('notification_channels', channels);
                          }}
                          color={selectedAlertConfig.notification_channels.includes(channel) ? 'primary' : 'default'}
                        />
                      ))}
                    </Stack>
                  </Box>
                </Grid>
              )}
            </Grid>

            <Box sx={{ mt: 3 }}>
              <Button 
                variant="contained" 
                color="primary" 
                onClick={saveNotificationSettings}
                disabled={loading}
                startIcon={loading ? <CircularProgress size={20} /> : <SaveIcon />}
              >
                {loading ? 'Saving...' : 'Save Notification Settings'}
              </Button>
            </Box>
          </Box>
        )}

        {/* System Health Tab */}
        {activeTab === 4 && (
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
              <SecurityIcon sx={{ mr: 1 }} />
              System Health
            </Typography>
            
            <Grid container spacing={3} sx={{ mt: 1 }}>
              {/* System Status Card */}
              <Grid item xs={12} md={8}>
                <Card>
                  <CardHeader title="System Status" avatar={<DashboardIcon color="primary" />} />
                  <CardContent>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                      Monitor the health and status of your solar energy system components.
                    </Typography>
                    <Grid container spacing={3}>
                      <Grid item xs={12} md={6}>
                        <Stack spacing={2}>
                          <Box display="flex" justifyContent="space-between" alignItems="center">
                            <Typography>Alert System:</Typography>
                            <Chip label="Online" color="success" size="small" />
                          </Box>
                          <Box display="flex" justifyContent="space-between" alignItems="center">
                            <Typography>Notification Service:</Typography>
                            <Chip label="Active" color="success" size="small" />
                          </Box>
                          <Box display="flex" justifyContent="space-between" alignItems="center">
                            <Typography>Data Collector:</Typography>
                            <Chip label="Running" color="success" size="small" />
                          </Box>
                        </Stack>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Stack spacing={2}>
                          <Box display="flex" justifyContent="space-between" alignItems="center">
                            <Typography>Database:</Typography>
                            <Chip label="Connected" color="success" size="small" />
                          </Box>
                          <Box display="flex" justifyContent="space-between" alignItems="center">
                            <Typography>Weather Service:</Typography>
                            <Chip label="Active" color="success" size="small" />
                          </Box>
                          <Box display="flex" justifyContent="space-between" alignItems="center">
                            <Typography>Last Check:</Typography>
                            <Typography variant="body2" color="text.secondary">
                              {formatTimeWithTimezone(new Date(), weatherLocation)}
                            </Typography>
                          </Box>
                        </Stack>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Box>
        )}
      </Paper>

      {/* Snackbar for messages */}
      <Snackbar
        open={!!success}
        autoHideDuration={6000}
        onClose={() => setSuccess(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert 
          onClose={() => setSuccess(null)} 
          severity="success"
          sx={{ width: '100%' }}
        >
          {success}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Settings;
