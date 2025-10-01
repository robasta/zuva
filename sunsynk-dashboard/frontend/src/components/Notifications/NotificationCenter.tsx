import React, { useState, useEffect } from 'react';
import {
  Badge,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Typography,
  Box,
  Chip,
  Button,
  Divider,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Switch,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel
} from '@mui/material';
import {
  Notifications as NotificationsIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  CheckCircle as CheckCircleIcon,
  Settings as SettingsIcon,
  Close as CloseIcon,
  VolumeUp as VolumeUpIcon
} from '@mui/icons-material';
import apiService from '../../services/apiService';

interface AlertData {
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
  enabled_channels: string[];
  quiet_hours_start: string;
  quiet_hours_end: string;
  severity_thresholds: Record<string, string>;
  emergency_voice_calls: boolean;
  max_notifications_per_hour: number;
}

const NotificationCenter: React.FC = () => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [activeAlertCount, setActiveAlertCount] = useState(0);
  const [preferences, setPreferences] = useState<NotificationPreferences>({
    enabled_channels: ['push', 'email'],
    quiet_hours_start: '22:00',
    quiet_hours_end: '06:00',
    severity_thresholds: {
      battery_low: 'medium',
      battery_critical: 'critical',
      grid_outage: 'high',
      inverter_offline: 'high',
      consumption_anomaly: 'low'
    },
    emergency_voice_calls: true,
    max_notifications_per_hour: 10
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const response = await apiService.getAlerts();
      if (response.success && response.data) {
        setAlerts(response.data.alerts || []);
        setActiveAlertCount(response.data.active_count || 0);
      }
    } catch (err: any) {
      setError(`Failed to fetch alerts: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchPreferences = async () => {
    try {
      const response = await apiService.getNotificationPreferences();
      if (response.success && response.data) {
        setPreferences(response.data);
      }
    } catch (err: any) {
      console.error('Failed to fetch notification preferences:', err);
    }
  };

  const updatePreferences = async () => {
    try {
      setLoading(true);
      await apiService.updateNotificationPreferences(preferences);
      setSettingsOpen(false);
      setError(null);
    } catch (err: any) {
      setError(`Failed to update preferences: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const acknowledgeAlert = async (alertId: string) => {
    try {
      const response = await apiService.acknowledgeAlert(alertId);
      if (response.success) {
        await fetchAlerts();
      }
    } catch (err: any) {
      setError(`Failed to acknowledge alert: ${err.message}`);
    }
  };

  const createTestAlert = async (severity: string = 'low') => {
    try {
      await apiService.createTestAlert(severity);
      await fetchAlerts();
    } catch (err: any) {
      setError(`Failed to create test alert: ${err.message}`);
    }
  };

  useEffect(() => {
    fetchAlerts();
    fetchPreferences();
    
    // Refresh alerts every 30 seconds
    const interval = setInterval(fetchAlerts, 30000);
    
    return () => clearInterval(interval);
  }, []);

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
        return <InfoIcon />;
    }
  };

  const getSeverityColor = (severity: string) => {
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

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <>
      {/* Notification Bell Icon */}
      <IconButton
        color="inherit"
        onClick={() => setDrawerOpen(true)}
        sx={{ mr: 1 }}
      >
        <Badge badgeContent={activeAlertCount} color="error" max={99}>
          <NotificationsIcon />
        </Badge>
      </IconButton>

      {/* Notification Drawer */}
      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        PaperProps={{
          sx: { width: 400, maxWidth: '90vw' }
        }}
      >
        <Box sx={{ p: 2 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6" component="div">
              🔔 Notifications
            </Typography>
            <Box>
              <IconButton onClick={() => setSettingsOpen(true)} size="small">
                <SettingsIcon />
              </IconButton>
              <IconButton onClick={() => setDrawerOpen(false)} size="small">
                <CloseIcon />
              </IconButton>
            </Box>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <Box display="flex" gap={1} mb={2}>
            <Button 
              size="small" 
              variant="outlined" 
              onClick={() => createTestAlert('low')}
            >
              Test Low
            </Button>
            <Button 
              size="small" 
              variant="outlined" 
              color="warning"
              onClick={() => createTestAlert('medium')}
            >
              Test Medium
            </Button>
            <Button 
              size="small" 
              variant="outlined" 
              color="error"
              onClick={() => createTestAlert('critical')}
            >
              Test Critical
            </Button>
          </Box>

          {loading ? (
            <Typography>Loading alerts...</Typography>
          ) : alerts.length === 0 ? (
            <Typography color="text.secondary" textAlign="center" sx={{ mt: 4 }}>
              No notifications
            </Typography>
          ) : (
            <List>
              {alerts.map((alert, index) => (
                <React.Fragment key={alert.id}>
                  <ListItem
                    alignItems="flex-start"
                    sx={{
                      border: 1,
                      borderColor: alert.status === 'active' ? getSeverityColor(alert.severity) + '.main' : 'grey.300',
                      borderRadius: 1,
                      mb: 1,
                      backgroundColor: alert.status === 'active' ? 'background.paper' : 'grey.50'
                    }}
                  >
                    <ListItemIcon>
                      {getSeverityIcon(alert.severity)}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box display="flex" justifyContent="space-between" alignItems="center">
                          <Typography variant="subtitle2">
                            {alert.title}
                          </Typography>
                          <Chip 
                            label={alert.severity.toUpperCase()} 
                            size="small"
                            color={getSeverityColor(alert.severity) as any}
                            variant={alert.status === 'active' ? 'filled' : 'outlined'}
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            {alert.message}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {formatTimestamp(alert.timestamp)}
                          </Typography>
                          {alert.status === 'active' && (
                            <Box mt={1}>
                              <Button
                                size="small"
                                variant="outlined"
                                onClick={() => acknowledgeAlert(alert.id)}
                              >
                                Acknowledge
                              </Button>
                            </Box>
                          )}
                          {alert.status === 'acknowledged' && (
                            <Typography variant="caption" color="success.main">
                              ✓ Acknowledged {alert.acknowledged_at ? formatTimestamp(alert.acknowledged_at) : ''}
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                  {index < alerts.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          )}
        </Box>
      </Drawer>

      {/* Settings Dialog */}
      <Dialog open={settingsOpen} onClose={() => setSettingsOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box display="flex" alignItems="center" gap={1}>
            <SettingsIcon />
            Notification Settings
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <Typography variant="h6" gutterBottom>
              Notification Channels
            </Typography>
            
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.enabled_channels.includes('push')}
                  onChange={(e) => {
                    const channels = e.target.checked 
                      ? [...preferences.enabled_channels, 'push']
                      : preferences.enabled_channels.filter(c => c !== 'push');
                    setPreferences({...preferences, enabled_channels: channels});
                  }}
                />
              }
              label="Push Notifications (Real-time)"
            />
            <br />
            
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.enabled_channels.includes('email')}
                  onChange={(e) => {
                    const channels = e.target.checked 
                      ? [...preferences.enabled_channels, 'email']
                      : preferences.enabled_channels.filter(c => c !== 'email');
                    setPreferences({...preferences, enabled_channels: channels});
                  }}
                />
              }
              label="Email Notifications"
            />
            <br />
            
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.enabled_channels.includes('sms')}
                  onChange={(e) => {
                    const channels = e.target.checked 
                      ? [...preferences.enabled_channels, 'sms']
                      : preferences.enabled_channels.filter(c => c !== 'sms');
                    setPreferences({...preferences, enabled_channels: channels});
                  }}
                />
              }
              label="SMS Notifications"
            />
            <br />
            
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.enabled_channels.includes('whatsapp')}
                  onChange={(e) => {
                    const channels = e.target.checked 
                      ? [...preferences.enabled_channels, 'whatsapp']
                      : preferences.enabled_channels.filter(c => c !== 'whatsapp');
                    setPreferences({...preferences, enabled_channels: channels});
                  }}
                />
              }
              label="WhatsApp Notifications"
            />

            <Divider sx={{ my: 3 }} />
            
            <Typography variant="h6" gutterBottom>
              Emergency Settings
            </Typography>
            
            <FormControlLabel
              control={
                <Switch
                  checked={preferences.emergency_voice_calls}
                  onChange={(e) => setPreferences({...preferences, emergency_voice_calls: e.target.checked})}
                  icon={<VolumeUpIcon />}
                />
              }
              label="Voice Calls for Critical Battery Alerts (REQ-014)"
            />

            <Divider sx={{ my: 3 }} />
            
            <Typography variant="h6" gutterBottom>
              Quiet Hours
            </Typography>
            
            <Box display="flex" gap={2} mb={2}>
              <TextField
                label="Start Time"
                type="time"
                value={preferences.quiet_hours_start}
                onChange={(e) => setPreferences({...preferences, quiet_hours_start: e.target.value})}
                InputLabelProps={{ shrink: true }}
                inputProps={{ step: 300 }}
                size="small"
              />
              <TextField
                label="End Time"
                type="time"
                value={preferences.quiet_hours_end}
                onChange={(e) => setPreferences({...preferences, quiet_hours_end: e.target.value})}
                InputLabelProps={{ shrink: true }}
                inputProps={{ step: 300 }}
                size="small"
              />
            </Box>

            <TextField
              label="Max Notifications Per Hour"
              type="number"
              value={preferences.max_notifications_per_hour}
              onChange={(e) => setPreferences({...preferences, max_notifications_per_hour: parseInt(e.target.value)})}
              size="small"
              fullWidth
              inputProps={{ min: 1, max: 60 }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSettingsOpen(false)}>Cancel</Button>
          <Button onClick={updatePreferences} variant="contained" disabled={loading}>
            {loading ? 'Saving...' : 'Save Settings'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default NotificationCenter;
