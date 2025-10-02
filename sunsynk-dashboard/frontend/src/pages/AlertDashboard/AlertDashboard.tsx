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
      // Get authentication token
      const token = localStorage.getItem('auth_token');
      if (!token) {
        console.warn('No auth token available for loading preferences');
        return;
      }
      
      // Load from persistent settings
      const response = await fetch('/api/settings/alerts', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        const settings = data.settings;
        
        if (settings && Object.keys(settings).length > 0) {
          setNotificationPrefs({
            email_enabled: settings.email_enabled ?? true,
            sms_enabled: settings.sms_enabled ?? false,
            push_enabled: settings.push_enabled ?? true,
            whatsapp_enabled: settings.whatsapp_enabled ?? false,
            voice_enabled: settings.voice_enabled ?? false,
            quiet_hours_enabled: settings.quiet_hours_enabled ?? false,
            quiet_start: settings.quiet_start ?? '22:00',
            quiet_end: settings.quiet_end ?? '07:00',
            severity_threshold: settings.severity_threshold ?? 'medium'
          });
        }
      }
    } catch (err: any) {
      console.error('Failed to load notification preferences:', err);
    }
  };

  const loadBatteryConfiguration = async () => {
    try {
      // Get authentication token
      const token = localStorage.getItem('auth_token');
      if (!token) {
        console.warn('No auth token available for loading battery config');
        return;
      }
      
      // Load from persistent settings
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
      // Get authentication token
      const token = localStorage.getItem('auth_token');
      if (!token) {
        throw new Error('Authentication required');
      }
      
      // Save notification preferences to persistent settings
      const response = await fetch('/api/settings/alerts', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          email_enabled: prefs.email_enabled,
          sms_enabled: prefs.sms_enabled,
          push_enabled: prefs.push_enabled,
          whatsapp_enabled: prefs.whatsapp_enabled,
          voice_enabled: prefs.voice_enabled,
          quiet_hours_enabled: prefs.quiet_hours_enabled,
          quiet_start: prefs.quiet_start,
          quiet_end: prefs.quiet_end,
          severity_threshold: prefs.severity_threshold
        })
      });

      if (response.ok) {
        setNotificationPrefs(prefs);
        setSnackbar({
          open: true,
          message: 'Notification preferences saved and will persist across restarts!',
          severity: 'success'
        });
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save preferences');
      }
    } catch (err: any) {
      setError(`Failed to update preferences: ${err.message}`);
    }
  };

  const saveBatteryConfiguration = async () => {
    try {
      setSavingBatteryConfig(true);
      
      // Get authentication token
      const token = localStorage.getItem('auth_token');
      if (!token) {
        throw new Error('Authentication required');
      }
      
      // Save battery configuration to persistent settings
      const response = await fetch('/api/settings/battery', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(batteryConfig)
      });

      if (response.ok) {
        setSnackbar({
          open: true,
          message: 'Battery configuration saved successfully and will persist across restarts!',
          severity: 'success'
        });
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save configuration');
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
    loadBatteryConfiguration();
    
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
