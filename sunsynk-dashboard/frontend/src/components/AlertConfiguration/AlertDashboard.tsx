import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Box,
  Grid,
  Chip,
  Button,
  Tabs,
  Tab,
  Stack,
  LinearProgress,
  Alert as MuiAlert,
  Badge,
  IconButton
} from '@mui/material';
import {
  Settings as SettingsIcon,
  History as HistoryIcon,
  TrendingUp as TrendingUpIcon,
  Notifications as NotificationsIcon,
  NotificationImportant as AlertIcon,
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import AlertConfiguration from './AlertConfiguration';
import AlertHistory from './AlertHistory';
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

interface MonitoringStatus {
  intelligent_monitoring: boolean;
  weather_intelligence: boolean;
  smart_alerts: boolean;
  last_check: string;
  next_check: string;
  configuration_valid: boolean;
}

const AlertDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [alertSummary, setAlertSummary] = useState<AlertSummary | null>(null);
  const [monitoringStatus, setMonitoringStatus] = useState<MonitoringStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
    
    // Refresh data every 30 seconds
    const interval = setInterval(loadDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load alert summary
      const alertResponse: any = await apiService.get('/alerts/summary');
      if (alertResponse.success) {
        setAlertSummary(alertResponse.summary);
      }

      // Load monitoring status
      const statusResponse: any = await apiService.get('/v1/alerts/status');
      if (statusResponse.success) {
        setMonitoringStatus(statusResponse.status);
      }
    } catch (error: any) {
      console.error('Failed to load dashboard data:', error);
      setError(error.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const getAlertCountColor = (count: number) => {
    if (count === 0) return 'success';
    if (count <= 5) return 'warning';
    return 'error';
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1">
          Intelligent Alert System
        </Typography>
        <IconButton onClick={loadDashboardData} disabled={loading}>
          <RefreshIcon />
        </IconButton>
      </Box>

      {error && (
        <MuiAlert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </MuiAlert>
      )}

      {/* Status Overview */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* Alert Summary */}
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Active Alerts
                  </Typography>
                  <Typography variant="h4">
                    {alertSummary?.active || 0}
                  </Typography>
                </Box>
                <Badge 
                  badgeContent={alertSummary?.active || 0} 
                  color={getAlertCountColor(alertSummary?.active || 0)}
                >
                  <AlertIcon fontSize="large" />
                </Badge>
              </Box>
              <Box mt={2}>
                <Stack direction="row" spacing={1}>
                  <Chip 
                    label={`Critical: ${alertSummary?.by_severity.critical || 0}`}
                    color="error"
                    size="small"
                  />
                  <Chip 
                    label={`High: ${alertSummary?.by_severity.high || 0}`}
                    color="warning"
                    size="small"
                  />
                </Stack>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Total Alerts */}
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Total Alerts (24h)
                  </Typography>
                  <Typography variant="h4">
                    {alertSummary?.total || 0}
                  </Typography>
                </Box>
                <HistoryIcon fontSize="large" color="primary" />
              </Box>
              <Box mt={2}>
                <Typography variant="body2" color="textSecondary">
                  {alertSummary?.resolved || 0} resolved, {alertSummary?.acknowledged || 0} acknowledged
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Monitoring Status */}
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Monitoring Status
                  </Typography>
                  <Stack direction="row" spacing={1} mt={1}>
                    <Chip
                      label="Intelligent"
                      color={monitoringStatus?.intelligent_monitoring ? "success" : "default"}
                      size="small"
                      icon={monitoringStatus?.intelligent_monitoring ? <CheckIcon /> : undefined}
                    />
                    <Chip
                      label="Weather"
                      color={monitoringStatus?.weather_intelligence ? "success" : "default"}
                      size="small"
                      icon={monitoringStatus?.weather_intelligence ? <CheckIcon /> : undefined}
                    />
                  </Stack>
                </Box>
                <TrendingUpIcon fontSize="large" color="info" />
              </Box>
              {monitoringStatus?.last_check && (
                <Typography variant="caption" color="textSecondary" mt={1}>
                  Last check: {formatDateTime(monitoringStatus.last_check)}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Configuration Status */}
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Configuration
                  </Typography>
                  <Chip
                    label={monitoringStatus?.configuration_valid ? "Valid" : "Needs Review"}
                    color={monitoringStatus?.configuration_valid ? "success" : "warning"}
                    icon={monitoringStatus?.configuration_valid ? <CheckIcon /> : <WarningIcon />}
                  />
                </Box>
                <SettingsIcon fontSize="large" color="action" />
              </Box>
              {monitoringStatus?.next_check && (
                <Typography variant="caption" color="textSecondary" mt={1}>
                  Next check: {formatDateTime(monitoringStatus.next_check)}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* Tab Navigation */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={handleTabChange}>
            <Tab 
              label="Configuration" 
              icon={<SettingsIcon />}
              iconPosition="start"
            />
            <Tab 
              label="History & Analytics" 
              icon={<HistoryIcon />}
              iconPosition="start"
            />
          </Tabs>
        </Box>

        {/* Tab Content */}
        <Box sx={{ p: 0 }}>
          {activeTab === 0 && (
            <AlertConfiguration />
          )}
          {activeTab === 1 && (
            <AlertHistory />
          )}
        </Box>
      </Card>

      {/* Quick Actions */}
      <Box sx={{ mt: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Quick Actions</Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            startIcon={<AlertIcon />}
            onClick={() => apiService.post('/alerts/test?severity=low')}
          >
            Test Low Priority Alert
          </Button>
          <Button
            variant="outlined"
            startIcon={<WarningIcon />}
            onClick={() => apiService.post('/alerts/test?severity=high')}
          >
            Test High Priority Alert
          </Button>
          <Button
            variant="outlined"
            startIcon={<NotificationsIcon />}
            onClick={() => apiService.post('/v1/alerts/config/validate')}
          >
            Validate Configuration
          </Button>
        </Stack>
      </Box>
    </Box>
  );
};

export default AlertDashboard;