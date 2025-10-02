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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  LinearProgress,
  Alert as MuiAlert
} from '@mui/material';
import {
  History as HistoryIcon,
  CheckCircle as CheckIcon,
  Cancel as CancelIcon,
  Info as InfoIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  FilterList as FilterIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  Visibility as ViewIcon
} from '@mui/icons-material';
import { formatDateTimeWithTimezone } from '../../utils/timezone';
import { apiService } from '../../services/apiService';

interface AlertHistoryItem {
  id: string;
  title: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'active' | 'acknowledged' | 'resolved';
  category: string;
  timestamp: string;
  acknowledged_at?: string;
  resolved_at?: string;
  metadata?: Record<string, any>;
}

interface WeatherPrediction {
  timestamp: string;
  predicted_solar_power: number;
  predicted_deficit: number;
  confidence: number;
  weather_factors: Record<string, any>;
  alert_recommended: boolean;
}

const AlertHistory: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertHistoryItem[]>([]);
  const [predictions, setPredictions] = useState<WeatherPrediction[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState<AlertHistoryItem | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [hoursBack, setHoursBack] = useState<number>(24);

  useEffect(() => {
    loadAlertHistory();
    loadWeatherPredictions();
  }, [hoursBack, filterSeverity, filterStatus]);

  const loadAlertHistory = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        hours: hoursBack.toString(),
        ...(filterSeverity !== 'all' && { severity: filterSeverity }),
        ...(filterStatus !== 'all' && { status: filterStatus })
      });
      
      const response: any = await apiService.get(`/alerts?${params}`);
      setAlerts(response.alerts || []);
    } catch (error: any) {
      console.error('Failed to load alert history:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadWeatherPredictions = async () => {
    try {
      const response: any = await apiService.get('/v1/alerts/weather/predictions?hours_ahead=6');
      if (response.success) {
        setPredictions(response.predictions || []);
      }
    } catch (error: any) {
      console.error('Failed to load weather predictions:', error);
    }
  };

  const acknowledgeAlert = async (alertId: string) => {
    try {
      await apiService.post(`/alerts/${alertId}/acknowledge`);
      await loadAlertHistory();
    } catch (error: any) {
      console.error('Failed to acknowledge alert:', error);
    }
  };

  const resolveAlert = async (alertId: string) => {
    try {
      await apiService.post(`/alerts/${alertId}/resolve`);
      await loadAlertHistory();
    } catch (error: any) {
      console.error('Failed to resolve alert:', error);
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <ErrorIcon color="error" />;
      case 'high':
        return <WarningIcon color="warning" />;
      case 'medium':
        return <InfoIcon color="info" />;
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
      default:
        return 'default';
    }
  };

  const getStatusColor = (status: string): "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning" => {
    switch (status) {
      case 'resolved':
        return 'success';
      case 'acknowledged':
        return 'info';
      case 'active':
        return 'warning';
      default:
        return 'default';
    }
  };

  const openDetailDialog = (alert: AlertHistoryItem) => {
    setSelectedAlert(alert);
    setDetailDialogOpen(true);
  };

  const formatDateTime = (dateString: string) => {
    return formatDateTimeWithTimezone(dateString);
  };

  return (
    <Box>
      {/* Alert History Card */}
      <Card sx={{ mb: 3 }}>
        <CardHeader
          title={
            <Box display="flex" alignItems="center">
              <HistoryIcon sx={{ mr: 2 }} />
              <Typography variant="h5">Alert History & Analytics</Typography>
            </Box>
          }
          action={
            <Stack direction="row" spacing={1}>
              <IconButton onClick={loadAlertHistory}>
                <RefreshIcon />
              </IconButton>
            </Stack>
          }
        />
        <CardContent>
          {/* Filters */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="Hours Back"
                type="number"
                value={hoursBack}
                onChange={(e) => setHoursBack(Number(e.target.value))}
                inputProps={{ min: 1, max: 168 }}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <FormControl fullWidth>
                <InputLabel>Severity</InputLabel>
                <Select
                  value={filterSeverity}
                  onChange={(e) => setFilterSeverity(e.target.value)}
                >
                  <MenuItem value="all">All</MenuItem>
                  <MenuItem value="low">Low</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="high">High</MenuItem>
                  <MenuItem value="critical">Critical</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={3}>
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                >
                  <MenuItem value="all">All</MenuItem>
                  <MenuItem value="active">Active</MenuItem>
                  <MenuItem value="acknowledged">Acknowledged</MenuItem>
                  <MenuItem value="resolved">Resolved</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={3}>
              <Button
                fullWidth
                variant="outlined"
                startIcon={<FilterIcon />}
                onClick={loadAlertHistory}
                sx={{ height: '56px' }}
              >
                Apply Filters
              </Button>
            </Grid>
          </Grid>

          {loading && <LinearProgress sx={{ mb: 2 }} />}

          {/* Alerts Table */}
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Severity</TableCell>
                  <TableCell>Title</TableCell>
                  <TableCell>Category</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Timestamp</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {alerts.map((alert) => (
                  <TableRow key={alert.id}>
                    <TableCell>
                      <Box display="flex" alignItems="center">
                        {getSeverityIcon(alert.severity)}
                        <Chip
                          label={alert.severity.toUpperCase()}
                          color={getSeverityColor(alert.severity)}
                          size="small"
                          sx={{ ml: 1 }}
                        />
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {alert.title}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {alert.message.substring(0, 80)}...
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={alert.category} variant="outlined" size="small" />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={alert.status.toUpperCase()}
                        color={getStatusColor(alert.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {formatDateTime(alert.timestamp)}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Stack direction="row" spacing={1}>
                        <Tooltip title="View Details">
                          <IconButton size="small" onClick={() => openDetailDialog(alert)}>
                            <ViewIcon />
                          </IconButton>
                        </Tooltip>
                        {alert.status === 'active' && (
                          <Tooltip title="Acknowledge">
                            <IconButton size="small" onClick={() => acknowledgeAlert(alert.id)}>
                              <CheckIcon color="primary" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {(alert.status === 'active' || alert.status === 'acknowledged') && (
                          <Tooltip title="Resolve">
                            <IconButton size="small" onClick={() => resolveAlert(alert.id)}>
                              <CancelIcon color="success" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
                {alerts.length === 0 && !loading && (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography color="text.secondary">
                        No alerts found for the selected criteria
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Weather Predictions Card */}
      <Card>
        <CardHeader
          title={
            <Typography variant="h6">Weather-Based Energy Predictions</Typography>
          }
        />
        <CardContent>
          {predictions.length > 0 ? (
            <Grid container spacing={2}>
              {predictions.slice(0, 6).map((prediction, index) => (
                <Grid item xs={12} md={6} lg={4} key={index}>
                  <Card variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="body2" color="text.secondary">
                      {formatDateTime(prediction.timestamp)}
                    </Typography>
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="body2">
                        Solar: {prediction.predicted_solar_power.toFixed(2)} kW
                      </Typography>
                      <Typography variant="body2">
                        Deficit: {prediction.predicted_deficit.toFixed(2)} kW
                      </Typography>
                      <Typography variant="body2">
                        Confidence: {(prediction.confidence * 100).toFixed(0)}%
                      </Typography>
                      {prediction.alert_recommended && (
                        <Chip
                          label="Alert Recommended"
                          color="warning"
                          size="small"
                          sx={{ mt: 1 }}
                        />
                      )}
                    </Box>
                  </Card>
                </Grid>
              ))}
            </Grid>
          ) : (
            <Typography color="text.secondary">
              No weather predictions available
            </Typography>
          )}
        </CardContent>
      </Card>

      {/* Detail Dialog */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Alert Details</DialogTitle>
        <DialogContent>
          {selectedAlert && (
            <Box>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6">{selectedAlert.title}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {selectedAlert.message}
                  </Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Stack spacing={1}>
                    <Chip
                      label={`Severity: ${selectedAlert.severity.toUpperCase()}`}
                      color={getSeverityColor(selectedAlert.severity)}
                    />
                    <Chip
                      label={`Status: ${selectedAlert.status.toUpperCase()}`}
                      color={getStatusColor(selectedAlert.status)}
                    />
                    <Chip
                      label={`Category: ${selectedAlert.category}`}
                      variant="outlined"
                    />
                  </Stack>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="body2">
                    <strong>Created:</strong> {formatDateTime(selectedAlert.timestamp)}
                  </Typography>
                  {selectedAlert.acknowledged_at && (
                    <Typography variant="body2">
                      <strong>Acknowledged:</strong> {formatDateTime(selectedAlert.acknowledged_at)}
                    </Typography>
                  )}
                  {selectedAlert.resolved_at && (
                    <Typography variant="body2">
                      <strong>Resolved:</strong> {formatDateTime(selectedAlert.resolved_at)}
                    </Typography>
                  )}
                </Grid>
                {selectedAlert.metadata && (
                  <Grid item xs={12}>
                    <Typography variant="subtitle2" sx={{ mt: 2 }}>Metadata:</Typography>
                    <pre style={{ fontSize: '12px', backgroundColor: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
                      {JSON.stringify(selectedAlert.metadata, null, 2)}
                    </pre>
                  </Grid>
                )}
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AlertHistory;