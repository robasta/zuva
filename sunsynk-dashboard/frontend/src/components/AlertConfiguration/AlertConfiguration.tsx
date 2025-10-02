import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Box,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Button,
  Slider,
  Chip,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
  Stack,
  Snackbar,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Settings as SettingsIcon,
  Battery4Bar as BatteryIcon,
  WbSunny as SunIcon,
  Notifications as NotificationsIcon,
  Schedule as ScheduleIcon,
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  Upload as UploadIcon,
  RestartAlt as ResetIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import { apiService } from '../../services/apiService';

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

const AlertConfigurationComponent: React.FC = () => {
  const [configurations, setConfigurations] = useState<AlertConfiguration[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<AlertConfiguration | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [expandedPanel, setExpandedPanel] = useState<string>('battery');

  useEffect(() => {
    loadConfigurations();
  }, []);

  const loadConfigurations = async () => {
    try {
      setLoading(true);
      const response: any = await apiService.get('/v1/alerts/config');
      setConfigurations(response.configurations || []);
      
      // Select first configuration if available
      if (response.configurations && response.configurations.length > 0) {
        setSelectedConfig(response.configurations[0]);
      } else {
        // Load default configuration
        await loadDefaultConfiguration();
      }
    } catch (error: any) {
      setMessage({ type: 'error', text: `Failed to load configurations: ${error.message}` });
    } finally {
      setLoading(false);
    }
  };

  const loadDefaultConfiguration = async () => {
    try {
      const response: any = await apiService.get('/v1/alerts/config/energy_deficit/defaults');
      setSelectedConfig(response.configuration);
    } catch (error: any) {
      setMessage({ type: 'error', text: `Failed to load default configuration: ${error.message}` });
    }
  };

  const saveConfiguration = async () => {
    if (!selectedConfig) return;

    try {
      setSaving(true);
      
      if (configurations.find(c => c.alert_type === selectedConfig.alert_type)) {
        // Update existing
        await apiService.put(`/v1/alerts/config/${selectedConfig.alert_type}`, selectedConfig);
      } else {
        // Create new
        await apiService.post('/v1/alerts/config', selectedConfig);
      }
      
      setMessage({ type: 'success', text: 'Configuration saved successfully!' });
      await loadConfigurations();
    } catch (error: any) {
      setMessage({ type: 'error', text: `Failed to save configuration: ${error.message}` });
    } finally {
      setSaving(false);
    }
  };

  const resetToDefaults = async () => {
    try {
      setLoading(true);
      await apiService.post('/v1/alerts/config/reset');
      setMessage({ type: 'success', text: 'Configurations reset to defaults!' });
      await loadConfigurations();
    } catch (error: any) {
      setMessage({ type: 'error', text: `Failed to reset configurations: ${error.message}` });
    } finally {
      setLoading(false);
    }
  };

  const exportConfiguration = async () => {
    try {
      const response: any = await apiService.post('/v1/alerts/config/export');
      const dataStr = JSON.stringify(response.export_data, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `alert-config-${new Date().toISOString().split('T')[0]}.json`;
      link.click();
      URL.revokeObjectURL(url);
      
      setMessage({ type: 'success', text: 'Configuration exported successfully!' });
    } catch (error: any) {
      setMessage({ type: 'error', text: `Failed to export configuration: ${error.message}` });
    }
  };

  const updateSelectedConfig = (path: string, value: any) => {
    if (!selectedConfig) return;
    
    const keys = path.split('.');
    const updatedConfig = { ...selectedConfig };
    let current: any = updatedConfig;
    
    for (let i = 0; i < keys.length - 1; i++) {
      current = current[keys[i]];
    }
    
    current[keys[keys.length - 1]] = value;
    setSelectedConfig(updatedConfig);
  };

  const handlePanelChange = (panel: string) => (event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpandedPanel(isExpanded ? panel : '');
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading alert configurations...</Typography>
      </Box>
    );
  }

  if (!selectedConfig) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>No configuration available</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Card>
        <CardHeader
          title={
            <Box display="flex" alignItems="center">
              <SettingsIcon sx={{ mr: 2 }} />
              <Typography variant="h5">Intelligent Alert Configuration</Typography>
            </Box>
          }
          action={
            <Stack direction="row" spacing={1}>
              <Tooltip title="Export Configuration">
                <IconButton onClick={exportConfiguration}>
                  <DownloadIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Reset to Defaults">
                <IconButton onClick={resetToDefaults}>
                  <ResetIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Refresh">
                <IconButton onClick={loadConfigurations}>
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
            </Stack>
          }
        />
        <CardContent>
          {/* Basic Settings */}
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
                        checked={selectedConfig.enabled}
                        onChange={(e) => updateSelectedConfig('enabled', e.target.checked)}
                      />
                    }
                    label="Enable Alerts"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth>
                    <InputLabel>Severity Filter</InputLabel>
                    <Select
                      value={selectedConfig.severity_filter}
                      onChange={(e) => updateSelectedConfig('severity_filter', e.target.value)}
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
                    value={selectedConfig.max_alerts_per_hour}
                    onChange={(e) => updateSelectedConfig('max_alerts_per_hour', Number(e.target.value))}
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
                    value={selectedConfig.battery_thresholds.min_level_threshold}
                    onChange={(_, value) => updateSelectedConfig('battery_thresholds.min_level_threshold', value)}
                    min={10}
                    max={80}
                    valueLabelDisplay="auto"
                    marks={[
                      { value: 20, label: '20%' },
                      { value: 40, label: '40%' },
                      { value: 60, label: '60%' }
                    ]}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography gutterBottom>Maximum Battery Loss (%)</Typography>
                  <Slider
                    value={selectedConfig.battery_thresholds.max_loss_threshold}
                    onChange={(_, value) => updateSelectedConfig('battery_thresholds.max_loss_threshold', value)}
                    min={5}
                    max={30}
                    valueLabelDisplay="auto"
                    marks={[
                      { value: 10, label: '10%' },
                      { value: 15, label: '15%' },
                      { value: 20, label: '20%' }
                    ]}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Critical Battery Level (%)"
                    type="number"
                    value={selectedConfig.battery_thresholds.critical_level}
                    onChange={(e) => updateSelectedConfig('battery_thresholds.critical_level', Number(e.target.value))}
                    inputProps={{ min: 5, max: 50 }}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Loss Timeframe (minutes)"
                    type="number"
                    value={selectedConfig.battery_thresholds.loss_timeframe_minutes}
                    onChange={(e) => updateSelectedConfig('battery_thresholds.loss_timeframe_minutes', Number(e.target.value))}
                    inputProps={{ min: 15, max: 240 }}
                  />
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>

          {/* Energy Deficit Settings */}
          <Accordion expanded={expandedPanel === 'energy'} onChange={handlePanelChange('energy')}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box display="flex" alignItems="center">
                <SunIcon sx={{ mr: 1 }} />
                <Typography variant="h6">Energy Deficit Settings</Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Deficit Threshold (kW)"
                    type="number"
                    value={selectedConfig.energy_thresholds.deficit_threshold_kw}
                    onChange={(e) => updateSelectedConfig('energy_thresholds.deficit_threshold_kw', Number(e.target.value))}
                    inputProps={{ min: 0.1, max: 10, step: 0.1 }}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Sustained Deficit (minutes)"
                    type="number"
                    value={selectedConfig.energy_thresholds.sustained_deficit_minutes}
                    onChange={(e) => updateSelectedConfig('energy_thresholds.sustained_deficit_minutes', Number(e.target.value))}
                    inputProps={{ min: 5, max: 120 }}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Prediction Horizon (hours)"
                    type="number"
                    value={selectedConfig.energy_thresholds.prediction_horizon_hours}
                    onChange={(e) => updateSelectedConfig('energy_thresholds.prediction_horizon_hours', Number(e.target.value))}
                    inputProps={{ min: 1, max: 12 }}
                  />
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>

          {/* Daylight Configuration */}
          <Accordion expanded={expandedPanel === 'daylight'} onChange={handlePanelChange('daylight')}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box display="flex" alignItems="center">
                <ScheduleIcon sx={{ mr: 1 }} />
                <Typography variant="h6">Daylight Configuration</Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Daylight Buffer (minutes)"
                    type="number"
                    value={selectedConfig.daylight_config.daylight_buffer_minutes}
                    onChange={(e) => updateSelectedConfig('daylight_config.daylight_buffer_minutes', Number(e.target.value))}
                    inputProps={{ min: 0, max: 120 }}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={selectedConfig.daylight_config.use_civil_twilight}
                        onChange={(e) => updateSelectedConfig('daylight_config.use_civil_twilight', e.target.checked)}
                      />
                    }
                    label="Include Civil Twilight"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Summer Buffer (minutes)"
                    type="number"
                    value={selectedConfig.summer_daylight_buffer}
                    onChange={(e) => updateSelectedConfig('summer_daylight_buffer', Number(e.target.value))}
                    inputProps={{ min: 0, max: 120 }}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Winter Buffer (minutes)"
                    type="number"
                    value={selectedConfig.winter_daylight_buffer}
                    onChange={(e) => updateSelectedConfig('winter_daylight_buffer', Number(e.target.value))}
                    inputProps={{ min: 0, max: 120 }}
                  />
                </Grid>
              </Grid>
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
                        checked={selectedConfig.weather_intelligence_enabled}
                        onChange={(e) => updateSelectedConfig('weather_intelligence_enabled', e.target.checked)}
                      />
                    }
                    label="Weather Intelligence"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={selectedConfig.machine_learning_enabled}
                        onChange={(e) => updateSelectedConfig('machine_learning_enabled', e.target.checked)}
                      />
                    }
                    label="Machine Learning"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={selectedConfig.predictive_alerts_enabled}
                        onChange={(e) => updateSelectedConfig('predictive_alerts_enabled', e.target.checked)}
                      />
                    }
                    label="Predictive Alerts"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={selectedConfig.auto_threshold_adjustment}
                        onChange={(e) => updateSelectedConfig('auto_threshold_adjustment', e.target.checked)}
                      />
                    }
                    label="Auto Threshold Adjustment"
                  />
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>

          {/* Notification Channels */}
          <Accordion expanded={expandedPanel === 'notifications'} onChange={handlePanelChange('notifications')}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box display="flex" alignItems="center">
                <NotificationsIcon sx={{ mr: 1 }} />
                <Typography variant="h6">Notification Channels</Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Select notification channels for alerts:
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  {['email', 'sms', 'whatsapp', 'push', 'voice'].map((channel) => (
                    <Chip
                      key={channel}
                      label={channel.toUpperCase()}
                      variant={selectedConfig.notification_channels.includes(channel) ? 'filled' : 'outlined'}
                      onClick={() => {
                        const channels = selectedConfig.notification_channels.includes(channel)
                          ? selectedConfig.notification_channels.filter(c => c !== channel)
                          : [...selectedConfig.notification_channels, channel];
                        updateSelectedConfig('notification_channels', channels);
                      }}
                      color={selectedConfig.notification_channels.includes(channel) ? 'primary' : 'default'}
                    />
                  ))}
                </Stack>
              </Box>
            </AccordionDetails>
          </Accordion>

          {/* Save Actions */}
          <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Configuration for {selectedConfig.alert_type} alerts
            </Typography>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={saveConfiguration}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Configuration'}
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* Snackbar for messages */}
      <Snackbar
        open={!!message}
        autoHideDuration={6000}
        onClose={() => setMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert 
          onClose={() => setMessage(null)} 
          severity={message?.type}
          sx={{ width: '100%' }}
        >
          {message?.text}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default AlertConfigurationComponent;