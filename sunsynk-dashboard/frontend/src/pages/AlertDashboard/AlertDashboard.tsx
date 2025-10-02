import React, { useState, useEffect } from 'react';
import {
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  CardHeader,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stack,
  Paper,
  LinearProgress,
  Tooltip,
  Badge,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Switch,
  FormControlLabel,
  Slider,
  Snackbar
} from '@mui/material';
import {
  Notifications as NotificationsIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  CheckCircle as CheckCircleIcon,
  Schedule as ScheduleIcon,
  Settings as SettingsIcon,
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
  ExpandMore as ExpandMoreIcon,
  NotificationsPaused as NotificationsPausedIcon,
  NotificationsActive as NotificationsActiveIcon,
  History as HistoryIcon,
  TrendingUp as TrendingUpIcon,
  Battery4Bar as BatteryIcon,
  WbSunny as SunIcon,
  CloudQueue as CloudIcon,
  ElectricalServices as GridIcon,
  Assignment as TestIcon,
  Visibility as ViewIcon,
  VisibilityOff as VisibilityOffIcon,
  Save as SaveIcon
} from '@mui/icons-material';
import { apiService } from '../../services/apiService';

interface AlertSummary {
  total: number;
  active: number;
  acknowledged: number;
  resolved: number;
  by_severity: {
    low: number;
    medium: number;
    high: number;
    critical: number;
  };
}

interface AlertItem {
  id: string;
  title: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'active' | 'acknowledged' | 'resolved';
  category: string;
  timestamp: string;
  acknowledged_at?: string;
  resolved_at?: string;
  metadata?: any;
}

interface NotificationPreferences {
  email_enabled: boolean;
  sms_enabled: boolean;
  push_enabled: boolean;
  whatsapp_enabled: boolean;
  voice_enabled: boolean;
  quiet_hours_enabled: boolean;
  quiet_start: string;
  quiet_end: string;
  severity_threshold: string;
}

const AlertDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Alert data
  const [alertSummary, setAlertSummary] = useState<AlertSummary | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [filteredAlerts, setFilteredAlerts] = useState<AlertItem[]>([]);
  
  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [hoursFilter, setHoursFilter] = useState<number>(24);
  
  // Notification preferences
  const [notificationPrefs, setNotificationPrefs] = useState<NotificationPreferences>({
    email_enabled: true,
    sms_enabled: false,
    push_enabled: true,
    whatsapp_enabled: false,
    voice_enabled: false,
    quiet_hours_enabled: false,
    quiet_start: '22:00',
    quiet_end: '07:00',
    severity_threshold: 'medium'
  });
  
  // Battery configuration state
  const [batteryConfig, setBatteryConfig] = useState({
    min_level_threshold: 30,
    critical_level: 15,
    max_loss_threshold: 10,
    loss_timeframe_minutes: 60
  });
  const [savingBatteryConfig, setSavingBatteryConfig] = useState(false);
  
  // Snackbar state
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error' | 'warning' | 'info'
  });
  
  // Dialog states
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState<AlertItem | null>(null);
  const [alertDetailOpen, setAlertDetailOpen] = useState(false);

  const loadAlertSummary = async () => {
    try {
      const response = await apiService.get<{success: boolean, summary: AlertSummary}>('/alerts/summary');
      if (response.success) {
        setAlertSummary(response.summary);
      }
    } catch (err: any) {
      setError(`Failed to load alert summary: ${err.message}`);
    }
  };

  const loadAlerts = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (statusFilter !== 'all') params.append('status', statusFilter);
      if (severityFilter !== 'all') params.append('severity', severityFilter);
      params.append('hours', hoursFilter.toString());
      
      const response = await apiService.get<{alerts: AlertItem[], total: number}>(`/alerts?${params.toString()}`);
      setAlerts(response.alerts || []);
      setFilteredAlerts(response.alerts || []);
    } catch (err: any) {
      setError(`Failed to load alerts: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadNotificationPreferences = async () => {
    try {
      const response = await apiService.get<NotificationPreferences>('/notifications/preferences');
      setNotificationPrefs(response);
    } catch (err: any) {
      console.error('Failed to load notification preferences:', err);
    }
  };

  const acknowledgeAlert = async (alertId: string) => {
    try {
      await apiService.post(`/alerts/${alertId}/acknowledge`);
      await loadAlerts();
      await loadAlertSummary();
    } catch (err: any) {
      setError(`Failed to acknowledge alert: ${err.message}`);
    }
  };

  const resolveAlert = async (alertId: string) => {
    try {
      await apiService.post(`/alerts/${alertId}/resolve`);
      await loadAlerts();
      await loadAlertSummary();
    } catch (err: any) {
      setError(`Failed to resolve alert: ${err.message}`);
    }
  };

  const createTestAlert = async (severity: string = 'low') => {
    try {
      await apiService.post(`/alerts/test?severity=${severity}`);
      await loadAlerts();
      await loadAlertSummary();
    } catch (err: any) {
      setError(`Failed to create test alert: ${err.message}`);
    }
  };

  const updateNotificationPreferences = async (prefs: NotificationPreferences) => {
    try {
      await apiService.put('/notifications/preferences', prefs);
      setNotificationPrefs(prefs);
    } catch (err: any) {
      setError(`Failed to update preferences: ${err.message}`);
    }
  };

  const saveBatteryConfiguration = async () => {
    try {
      setSavingBatteryConfig(true);
      
      // Update battery alert configuration via API
      const response = await fetch('/api/v1/alerts/config/battery_critical', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          enabled: true,
          battery_thresholds: batteryConfig,
          notification_channels: ['email', 'sms', 'push'],
          severity_filter: 'medium'
        })
      });

      if (response.ok) {
        setSnackbar({
          open: true,
          message: 'Battery configuration saved successfully!',
          severity: 'success'
        });
      } else {
        throw new Error('Failed to save configuration');
      }
    } catch (error: any) {
      setSnackbar({
        open: true,
        message: `Failed to save battery configuration: ${error.message}`,
        severity: 'error'
      });
    } finally {
      setSavingBatteryConfig(false);
    }
  };

  useEffect(() => {
    loadAlertSummary();
    loadAlerts();
    loadNotificationPreferences();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      loadAlertSummary();
      loadAlerts();
    }, 30000);
    
    return () => clearInterval(interval);
  }, [statusFilter, severityFilter, hoursFilter]);

  useEffect(() => {
    // Apply client-side filtering
    let filtered = alerts;
    
    if (categoryFilter !== 'all') {
      filtered = filtered.filter(alert => alert.category === categoryFilter);
    }
    
    setFilteredAlerts(filtered);
  }, [alerts, categoryFilter]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
    setError(null);
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <ErrorIcon color="error" />;
      case 'high':
        return <WarningIcon color="warning" />;
      case 'medium':
        return <InfoIcon color="info" />;
      case 'low':
        return <CheckCircleIcon color="success" />;
      default:
        return <InfoIcon color="disabled" />;
    }
  };

  const getSeverityColor = (severity: string): "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning" => {
    switch (severity) {
      case 'critical':
        return 'error';
      case 'high':
        return 'warning';
      case 'medium':
        return 'info';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <NotificationsActiveIcon color="error" />;
      case 'acknowledged':
        return <ScheduleIcon color="warning" />;
      case 'resolved':
        return <CheckCircleIcon color="success" />;
      default:
        return <InfoIcon color="disabled" />;
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'battery':
        return <BatteryIcon />;
      case 'solar':
        return <SunIcon />;
      case 'grid':
        return <GridIcon />;
      case 'weather':
        return <CloudIcon />;
      case 'system':
        return <SettingsIcon />;
      default:
        return <NotificationsIcon />;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const getUniqueCategories = () => {
    const categories = [...new Set(alerts.map(alert => alert.category))];
    return categories;
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" sx={{ fontWeight: 600, mb: 3, display: 'flex', alignItems: 'center' }}>
        <NotificationsIcon sx={{ mr: 2, color: 'primary.main' }} />
        Alert Management Dashboard
      </Typography>
      
      <Typography variant="body1" sx={{ mb: 4, color: 'text.secondary' }}>
        Monitor, manage, and configure your solar system alerts and notifications.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Alert Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h4" color="primary">
                    {alertSummary?.total || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Alerts
                  </Typography>
                </Box>
                <NotificationsIcon color="primary" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h4" color="error">
                    {alertSummary?.active || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Active Alerts
                  </Typography>
                </Box>
                <NotificationsActiveIcon color="error" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h4" color="warning">
                    {alertSummary?.acknowledged || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Acknowledged
                  </Typography>
                </Box>
                <ScheduleIcon color="warning" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h4" color="success">
                    {alertSummary?.resolved || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Resolved
                  </Typography>
                </Box>
                <CheckCircleIcon color="success" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Severity Breakdown */}
      {alertSummary && (
        <Card sx={{ mb: 4 }}>
          <CardHeader title="Alert Severity Breakdown" />
          <CardContent>
            <Grid container spacing={2}>
              <Grid item xs={3}>
                <Box textAlign="center">
                  <Typography variant="h5" color="error">
                    {alertSummary.by_severity.critical}
                  </Typography>
                  <Chip label="Critical" color="error" size="small" />
                </Box>
              </Grid>
              <Grid item xs={3}>
                <Box textAlign="center">
                  <Typography variant="h5" color="warning">
                    {alertSummary.by_severity.high}
                  </Typography>
                  <Chip label="High" color="warning" size="small" />
                </Box>
              </Grid>
              <Grid item xs={3}>
                <Box textAlign="center">
                  <Typography variant="h5" color="info">
                    {alertSummary.by_severity.medium}
                  </Typography>
                  <Chip label="Medium" color="info" size="small" />
                </Box>
              </Grid>
              <Grid item xs={3}>
                <Box textAlign="center">
                  <Typography variant="h5" color="success">
                    {alertSummary.by_severity.low}
                  </Typography>
                  <Chip label="Low" color="success" size="small" />
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={handleTabChange} aria-label="Alert Dashboard tabs">
          <Tab 
            label="Active Alerts" 
            icon={<NotificationsActiveIcon />} 
            iconPosition="start"
          />
          <Tab 
            label="Alert History" 
            icon={<HistoryIcon />} 
            iconPosition="start"
          />
          <Tab 
            label="Configuration" 
            icon={<SettingsIcon />} 
            iconPosition="start"
          />
          <Tab 
            label="Test & Monitoring" 
            icon={<TestIcon />} 
            iconPosition="start"
          />
        </Tabs>
      </Box>

      {/* Active Alerts Tab */}
      {activeTab === 0 && (
        <Box>
          {/* Filters */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
                <FilterIcon sx={{ mr: 1 }} />
                Filters
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={2}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Status</InputLabel>
                    <Select
                      value={statusFilter}
                      label="Status"
                      onChange={(e) => setStatusFilter(e.target.value)}
                    >
                      <MenuItem value="all">All Status</MenuItem>
                      <MenuItem value="active">Active</MenuItem>
                      <MenuItem value="acknowledged">Acknowledged</MenuItem>
                      <MenuItem value="resolved">Resolved</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6} md={2}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Severity</InputLabel>
                    <Select
                      value={severityFilter}
                      label="Severity"
                      onChange={(e) => setSeverityFilter(e.target.value)}
                    >
                      <MenuItem value="all">All Severities</MenuItem>
                      <MenuItem value="critical">Critical</MenuItem>
                      <MenuItem value="high">High</MenuItem>
                      <MenuItem value="medium">Medium</MenuItem>
                      <MenuItem value="low">Low</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6} md={2}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Category</InputLabel>
                    <Select
                      value={categoryFilter}
                      label="Category"
                      onChange={(e) => setCategoryFilter(e.target.value)}
                    >
                      <MenuItem value="all">All Categories</MenuItem>
                      {getUniqueCategories().map(category => (
                        <MenuItem key={category} value={category}>{category}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6} md={2}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Time Range</InputLabel>
                    <Select
                      value={hoursFilter}
                      label="Time Range"
                      onChange={(e) => setHoursFilter(Number(e.target.value))}
                    >
                      <MenuItem value={1}>Last 1 Hour</MenuItem>
                      <MenuItem value={6}>Last 6 Hours</MenuItem>
                      <MenuItem value={24}>Last 24 Hours</MenuItem>
                      <MenuItem value={72}>Last 3 Days</MenuItem>
                      <MenuItem value={168}>Last Week</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6} md={2}>
                  <Button
                    variant="outlined"
                    startIcon={<RefreshIcon />}
                    onClick={() => {
                      loadAlerts();
                      loadAlertSummary();
                    }}
                    fullWidth
                  >
                    Refresh
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Alert List */}
          <Card>
            <CardHeader 
              title={`Alerts (${filteredAlerts.length})`}
              action={
                <Chip 
                  label={`${filteredAlerts.filter(a => a.status === 'active').length} Active`}
                  color="error"
                  variant="outlined"
                />
              }
            />
            <CardContent>
              {loading ? (
                <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
                  <CircularProgress />
                </Box>
              ) : filteredAlerts.length === 0 ? (
                <Box textAlign="center" py={4}>
                  <NotificationsPausedIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary">
                    No alerts found
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    No alerts match your current filters
                  </Typography>
                </Box>
              ) : (
                <List>
                  {filteredAlerts.map((alert, index) => (
                    <React.Fragment key={alert.id}>
                      <ListItem>
                        <ListItemIcon>
                          <Badge 
                            color={getSeverityColor(alert.severity)}
                            variant="dot"
                            invisible={alert.status !== 'active'}
                          >
                            {getCategoryIcon(alert.category)}
                          </Badge>
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box display="flex" alignItems="center" gap={1}>
                              <Typography variant="subtitle1">
                                {alert.title}
                              </Typography>
                              <Chip 
                                label={alert.severity}
                                color={getSeverityColor(alert.severity)}
                                size="small"
                              />
                              <Chip 
                                label={alert.status}
                                color={alert.status === 'active' ? 'error' : alert.status === 'acknowledged' ? 'warning' : 'success'}
                                size="small"
                                variant="outlined"
                              />
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                                {alert.message}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {formatTimestamp(alert.timestamp)} • Category: {alert.category}
                              </Typography>
                            </Box>
                          }
                        />
                        <ListItemSecondaryAction>
                          <Stack direction="row" spacing={1}>
                            <Tooltip title="View Details">
                              <IconButton
                                size="small"
                                onClick={() => {
                                  setSelectedAlert(alert);
                                  setAlertDetailOpen(true);
                                }}
                              >
                                <ViewIcon />
                              </IconButton>
                            </Tooltip>
                            {alert.status === 'active' && (
                              <Tooltip title="Acknowledge">
                                <IconButton
                                  size="small"
                                  color="warning"
                                  onClick={() => acknowledgeAlert(alert.id)}
                                >
                                  <ScheduleIcon />
                                </IconButton>
                              </Tooltip>
                            )}
                            {(alert.status === 'active' || alert.status === 'acknowledged') && (
                              <Tooltip title="Resolve">
                                <IconButton
                                  size="small"
                                  color="success"
                                  onClick={() => resolveAlert(alert.id)}
                                >
                                  <CheckCircleIcon />
                                </IconButton>
                              </Tooltip>
                            )}
                          </Stack>
                        </ListItemSecondaryAction>
                      </ListItem>
                      {index < filteredAlerts.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Box>
      )}

      {/* Alert History Tab */}
      {activeTab === 1 && (
        <Box>
          <Card>
            <CardHeader title="Alert History" />
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                All alert history is displayed in the main alerts view. Use the filters above to view resolved alerts.
              </Typography>
            </CardContent>
          </Card>
        </Box>
      )}

      {/* Configuration Tab */}
      {activeTab === 2 && (
        <Box>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader title="Notification Channels" />
                <CardContent>
                  <Stack spacing={2}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={notificationPrefs.email_enabled}
                          onChange={(e) => updateNotificationPreferences({
                            ...notificationPrefs,
                            email_enabled: e.target.checked
                          })}
                        />
                      }
                      label="Email Notifications"
                    />
                    <FormControlLabel
                      control={
                        <Switch
                          checked={notificationPrefs.sms_enabled}
                          onChange={(e) => updateNotificationPreferences({
                            ...notificationPrefs,
                            sms_enabled: e.target.checked
                          })}
                        />
                      }
                      label="SMS Notifications"
                    />
                    <FormControlLabel
                      control={
                        <Switch
                          checked={notificationPrefs.push_enabled}
                          onChange={(e) => updateNotificationPreferences({
                            ...notificationPrefs,
                            push_enabled: e.target.checked
                          })}
                        />
                      }
                      label="Push Notifications"
                    />
                    <FormControlLabel
                      control={
                        <Switch
                          checked={notificationPrefs.whatsapp_enabled}
                          onChange={(e) => updateNotificationPreferences({
                            ...notificationPrefs,
                            whatsapp_enabled: e.target.checked
                          })}
                        />
                      }
                      label="WhatsApp Notifications"
                    />
                    <FormControlLabel
                      control={
                        <Switch
                          checked={notificationPrefs.voice_enabled}
                          onChange={(e) => updateNotificationPreferences({
                            ...notificationPrefs,
                            voice_enabled: e.target.checked
                          })}
                        />
                      }
                      label="Voice Call Notifications"
                    />
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader title="Alert Settings" />
                <CardContent>
                  <Stack spacing={3}>
                    <FormControl fullWidth>
                      <InputLabel>Minimum Severity</InputLabel>
                      <Select
                        value={notificationPrefs.severity_threshold}
                        label="Minimum Severity"
                        onChange={(e) => updateNotificationPreferences({
                          ...notificationPrefs,
                          severity_threshold: e.target.value
                        })}
                      >
                        <MenuItem value="low">Low</MenuItem>
                        <MenuItem value="medium">Medium</MenuItem>
                        <MenuItem value="high">High</MenuItem>
                        <MenuItem value="critical">Critical</MenuItem>
                      </Select>
                    </FormControl>

                    <FormControlLabel
                      control={
                        <Switch
                          checked={notificationPrefs.quiet_hours_enabled}
                          onChange={(e) => updateNotificationPreferences({
                            ...notificationPrefs,
                            quiet_hours_enabled: e.target.checked
                          })}
                        />
                      }
                      label="Enable Quiet Hours"
                    />

                    {notificationPrefs.quiet_hours_enabled && (
                      <Grid container spacing={2}>
                        <Grid item xs={6}>
                          <TextField
                            fullWidth
                            type="time"
                            label="Quiet Start"
                            value={notificationPrefs.quiet_start}
                            onChange={(e) => updateNotificationPreferences({
                              ...notificationPrefs,
                              quiet_start: e.target.value
                            })}
                            InputLabelProps={{ shrink: true }}
                          />
                        </Grid>
                        <Grid item xs={6}>
                          <TextField
                            fullWidth
                            type="time"
                            label="Quiet End"
                            value={notificationPrefs.quiet_end}
                            onChange={(e) => updateNotificationPreferences({
                              ...notificationPrefs,
                              quiet_end: e.target.value
                            })}
                            InputLabelProps={{ shrink: true }}
                          />
                        </Grid>
                      </Grid>
                    )}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            {/* Battery Thresholds Configuration */}
            <Grid item xs={12}>
              <Card>
                <CardHeader 
                  title="Battery Thresholds" 
                  avatar={<BatteryIcon color="primary" />}
                />
                <CardContent>
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <Stack spacing={3}>
                        <Box>
                          <Typography gutterBottom>
                            Battery Alert Level: {batteryConfig.min_level_threshold}%
                          </Typography>
                          <Slider
                            value={batteryConfig.min_level_threshold}
                            onChange={(_, value) => setBatteryConfig(prev => ({
                              ...prev,
                              min_level_threshold: value as number
                            }))}
                            min={10}
                            max={80}
                            valueLabelDisplay="auto"
                            marks={[
                              { value: 20, label: '20%' },
                              { value: 30, label: '30%' },
                              { value: 40, label: '40%' },
                              { value: 50, label: '50%' }
                            ]}
                            sx={{ mt: 2 }}
                          />
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            Alert when battery drops below this level
                          </Typography>
                        </Box>

                        <Box>
                          <Typography gutterBottom>
                            Critical Battery Level: {batteryConfig.critical_level}%
                          </Typography>
                          <Slider
                            value={batteryConfig.critical_level}
                            onChange={(_, value) => setBatteryConfig(prev => ({
                              ...prev,
                              critical_level: value as number
                            }))}
                            min={5}
                            max={30}
                            valueLabelDisplay="auto"
                            marks={[
                              { value: 10, label: '10%' },
                              { value: 15, label: '15%' },
                              { value: 20, label: '20%' }
                            ]}
                            sx={{ mt: 2 }}
                          />
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            Emergency alerts for critically low battery
                          </Typography>
                        </Box>
                      </Stack>
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <Stack spacing={3}>
                        <Box>
                          <Typography gutterBottom>
                            Battery Loss Alert: {batteryConfig.max_loss_threshold}% in {batteryConfig.loss_timeframe_minutes} min
                          </Typography>
                          <Slider
                            value={batteryConfig.max_loss_threshold}
                            onChange={(_, value) => setBatteryConfig(prev => ({
                              ...prev,
                              max_loss_threshold: value as number
                            }))}
                            min={5}
                            max={30}
                            valueLabelDisplay="auto"
                            marks={[
                              { value: 10, label: '10%' },
                              { value: 15, label: '15%' },
                              { value: 20, label: '20%' }
                            ]}
                            sx={{ mt: 2 }}
                          />
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            Alert when battery loses this percentage rapidly
                          </Typography>
                        </Box>

                        <TextField
                          fullWidth
                          type="number"
                          label="Loss Timeframe (minutes)"
                          value={batteryConfig.loss_timeframe_minutes}
                          onChange={(e) => setBatteryConfig(prev => ({
                            ...prev,
                            loss_timeframe_minutes: parseInt(e.target.value) || 60
                          }))}
                          inputProps={{ min: 15, max: 240 }}
                          helperText="Time window for detecting rapid battery loss"
                        />

                        <Button
                          variant="contained"
                          onClick={saveBatteryConfiguration}
                          disabled={savingBatteryConfig}
                          startIcon={savingBatteryConfig ? <CircularProgress size={20} /> : <SaveIcon />}
                        >
                          {savingBatteryConfig ? 'Saving...' : 'Save Battery Settings'}
                        </Button>
                      </Stack>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      {/* Test & Monitoring Tab */}
      {activeTab === 3 && (
        <Box>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader title="Test Alerts" />
                <CardContent>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    Create test alerts to verify your notification configuration.
                  </Typography>
                  <Stack spacing={2}>
                    <Button
                      variant="outlined"
                      color="success"
                      startIcon={<CheckCircleIcon />}
                      onClick={() => createTestAlert('low')}
                      fullWidth
                    >
                      Test Low Priority Alert
                    </Button>
                    <Button
                      variant="outlined"
                      color="info"
                      startIcon={<InfoIcon />}
                      onClick={() => createTestAlert('medium')}
                      fullWidth
                    >
                      Test Medium Priority Alert
                    </Button>
                    <Button
                      variant="outlined"
                      color="warning"
                      startIcon={<WarningIcon />}
                      onClick={() => createTestAlert('high')}
                      fullWidth
                    >
                      Test High Priority Alert
                    </Button>
                    <Button
                      variant="outlined"
                      color="error"
                      startIcon={<ErrorIcon />}
                      onClick={() => createTestAlert('critical')}
                      fullWidth
                    >
                      Test Critical Alert
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader title="System Status" />
                <CardContent>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Alert system monitoring and status
                  </Typography>
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
                      <Typography>Last Check:</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {new Date().toLocaleTimeString()}
                      </Typography>
                    </Box>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      {/* Alert Detail Dialog */}
      <Dialog
        open={alertDetailOpen}
        onClose={() => setAlertDetailOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Alert Details
        </DialogTitle>
        <DialogContent>
          {selectedAlert && (
            <Box>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" color="text.secondary">Title</Typography>
                  <Typography variant="body1">{selectedAlert.title}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" color="text.secondary">Severity</Typography>
                  <Chip 
                    label={selectedAlert.severity}
                    color={getSeverityColor(selectedAlert.severity)}
                    size="small"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" color="text.secondary">Status</Typography>
                  <Chip 
                    label={selectedAlert.status}
                    color={selectedAlert.status === 'active' ? 'error' : selectedAlert.status === 'acknowledged' ? 'warning' : 'success'}
                    size="small"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" color="text.secondary">Category</Typography>
                  <Typography variant="body1">{selectedAlert.category}</Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="subtitle2" color="text.secondary">Message</Typography>
                  <Typography variant="body1">{selectedAlert.message}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" color="text.secondary">Created</Typography>
                  <Typography variant="body1">{formatTimestamp(selectedAlert.timestamp)}</Typography>
                </Grid>
                {selectedAlert.acknowledged_at && (
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2" color="text.secondary">Acknowledged</Typography>
                    <Typography variant="body1">{formatTimestamp(selectedAlert.acknowledged_at)}</Typography>
                  </Grid>
                )}
                {selectedAlert.resolved_at && (
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2" color="text.secondary">Resolved</Typography>
                    <Typography variant="body1">{formatTimestamp(selectedAlert.resolved_at)}</Typography>
                  </Grid>
                )}
                {selectedAlert.metadata && Object.keys(selectedAlert.metadata).length > 0 && (
                  <Grid item xs={12}>
                    <Typography variant="subtitle2" color="text.secondary">Metadata</Typography>
                    <pre style={{ fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>
                      {JSON.stringify(selectedAlert.metadata, null, 2)}
                    </pre>
                  </Grid>
                )}
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          {selectedAlert?.status === 'active' && (
            <Button
              onClick={() => {
                acknowledgeAlert(selectedAlert.id);
                setAlertDetailOpen(false);
              }}
              color="warning"
              startIcon={<ScheduleIcon />}
            >
              Acknowledge
            </Button>
          )}
          {selectedAlert && (selectedAlert.status === 'active' || selectedAlert.status === 'acknowledged') && (
            <Button
              onClick={() => {
                resolveAlert(selectedAlert.id);
                setAlertDetailOpen(false);
              }}
              color="success"
              startIcon={<CheckCircleIcon />}
            >
              Resolve
            </Button>
          )}
          <Button onClick={() => setAlertDetailOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert 
          onClose={() => setSnackbar({ ...snackbar, open: false })} 
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default AlertDashboard;
