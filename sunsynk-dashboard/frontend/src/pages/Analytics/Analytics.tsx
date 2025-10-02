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
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  TrendingUp as TrendingUpIcon,
  Psychology as PsychologyIcon,
  Battery4Bar as BatteryIcon,
  WbSunny as SunIcon,
  CloudQueue as CloudIcon,
  Assessment as AssessmentIcon,
  AutoGraph as AutoGraphIcon,
  Lightbulb as LightbulbIcon
} from '@mui/icons-material';
import { apiService } from '../../services/apiService';
import { formatPower } from '../../utils/powerUtils';

interface WeatherCorrelation {
  correlation_coefficient: number;
  prediction_accuracy: number;
  optimal_conditions: any;
  efficiency_factors: any;
}

interface ConsumptionPattern {
  type: string;
  peak_hours: number[];
  average_consumption: number;
  peak_consumption: number;
  efficiency_score: number;
  confidence: number;
}

interface Anomaly {
  timestamp: string;
  expected: number;
  actual: number;
  deviation: number;
  type: string;
  severity: string;
}

interface Recommendation {
  category: string;
  title: string;
  description: string;
  potential_savings: string;
  confidence: number;
  priority: string;
}

interface BatteryOptimization {
  optimal_soc_range: { min: number; max: number };
  charge_schedule: any[];
  efficiency_improvements: any[];
  cost_savings: any;
}

const Analytics: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // ML Analytics Data
  const [weatherCorrelation, setWeatherCorrelation] = useState<any>(null);
  const [consumptionPatterns, setConsumptionPatterns] = useState<ConsumptionPattern[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [batteryOptimization, setBatteryOptimization] = useState<BatteryOptimization | null>(null);
  const [energyForecasting, setEnergyForecasting] = useState<any>(null);

  const loadWeatherAnalysis = async () => {
    try {
      setLoading(true);
      const response = await apiService.get<WeatherCorrelation>('/v6/weather/correlation?days=7');
      setWeatherCorrelation(response);
    } catch (err: any) {
      setError(`Weather analysis failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadConsumptionAnalysis = async () => {
    try {
      setLoading(true);
      const response = await apiService.get<{
        patterns: ConsumptionPattern[];
        anomalies: Anomaly[];
        optimization_recommendations: Recommendation[];
      }>('/v6/consumption/patterns?days=30');
      setConsumptionPatterns(response.patterns || []);
      setAnomalies(response.anomalies || []);
      setRecommendations(response.optimization_recommendations || []);
    } catch (err: any) {
      setError(`Consumption analysis failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadBatteryOptimization = async () => {
    try {
      setLoading(true);
      const response = await apiService.get<BatteryOptimization>('/v6/battery/optimization');
      setBatteryOptimization(response);
    } catch (err: any) {
      setError(`Battery optimization failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadEnergyForecasting = async () => {
    try {
      setLoading(true);
      const response = await apiService.get<any>('/v6/analytics/forecasting?hours=48');
      setEnergyForecasting(response);
    } catch (err: any) {
      setError(`Energy forecasting failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 0) loadWeatherAnalysis();
    else if (activeTab === 1) loadConsumptionAnalysis();
    else if (activeTab === 2) loadBatteryOptimization();
    else if (activeTab === 3) loadEnergyForecasting();
  }, [activeTab]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
    setError(null);
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'error';
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'default';
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" sx={{ fontWeight: 600, mb: 3, display: 'flex', alignItems: 'center' }}>
        <PsychologyIcon sx={{ mr: 2, color: 'primary.main' }} />
        ML-Powered Analytics
      </Typography>
      
      <Typography variant="body1" sx={{ mb: 4, color: 'text.secondary' }}>
        Advanced machine learning analysis of your solar energy system with intelligent insights and optimization recommendations.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={handleTabChange} aria-label="ML Analytics tabs">
          <Tab 
            label="Weather Correlation" 
            icon={<CloudIcon />} 
            iconPosition="start"
          />
          <Tab 
            label="Consumption Patterns" 
            icon={<TrendingUpIcon />} 
            iconPosition="start"
          />
          <Tab 
            label="Battery Optimization" 
            icon={<BatteryIcon />} 
            iconPosition="start"
          />
          <Tab 
            label="Energy Forecasting" 
            icon={<AutoGraphIcon />} 
            iconPosition="start"
          />
        </Tabs>
      </Box>

      {loading && (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
          <CircularProgress />
        </Box>
      )}

      {/* Weather Correlation Tab */}
      {activeTab === 0 && !loading && (
        <Box>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader 
                  title="Weather-Solar Correlation" 
                  avatar={<SunIcon color="primary" />}
                />
                <CardContent>
                  {weatherCorrelation ? (
                    <>
                      <Box sx={{ mb: 3 }}>
                        <Typography variant="body2" color="text.secondary">Correlation Coefficient</Typography>
                        <Typography variant="h4" color="primary">
                          {(weatherCorrelation.correlation_analysis?.correlation_coefficient * 100 || 0).toFixed(1)}%
                        </Typography>
                        <LinearProgress 
                          variant="determinate" 
                          value={(weatherCorrelation.correlation_analysis?.correlation_coefficient * 100) || 0}
                          sx={{ mt: 1 }}
                        />
                      </Box>
                      
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary">Prediction Accuracy</Typography>
                        <Chip 
                          label={`${(weatherCorrelation.correlation_analysis?.prediction_accuracy * 100 || 0).toFixed(1)}%`}
                          color={getConfidenceColor(weatherCorrelation.correlation_analysis?.prediction_accuracy || 0)}
                          variant="outlined"
                        />
                      </Box>

                      <Box>
                        <Typography variant="body2" color="text.secondary">Analysis Confidence</Typography>
                        <Chip 
                          label={weatherCorrelation.confidence || 'Medium'}
                          color={weatherCorrelation.confidence === 'high' ? 'success' : 'warning'}
                        />
                      </Box>
                    </>
                  ) : (
                    <Typography color="text.secondary">No correlation data available</Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader 
                  title="Production Forecast" 
                  avatar={<AssessmentIcon color="primary" />}
                />
                <CardContent>
                  {weatherCorrelation?.production_forecast ? (
                    <List dense>
                      {weatherCorrelation.production_forecast.slice(0, 6).map((forecast: any, index: number) => (
                        <ListItem key={index} divider>
                          <ListItemText
                            primary={`Hour ${index + 1}`}
                            secondary={formatPower(forecast.predicted_production || 0)}
                          />
                          <Chip 
                            size="small"
                            label={`${(forecast.confidence * 100)?.toFixed(0) || 0}%`}
                            color={getConfidenceColor(forecast.confidence || 0)}
                          />
                        </ListItem>
                      ))}
                    </List>
                  ) : (
                    <Typography color="text.secondary">No forecast data available</Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      {/* Consumption Patterns Tab */}
      {activeTab === 1 && !loading && (
        <Box>
          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <Card>
                <CardHeader 
                  title="Detected Consumption Patterns" 
                  avatar={<TrendingUpIcon color="primary" />}
                />
                <CardContent>
                  {consumptionPatterns.length > 0 ? (
                    consumptionPatterns.map((pattern, index) => (
                      <Accordion key={index}>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                            <Typography sx={{ flexGrow: 1 }}>
                              {pattern.type} Pattern
                            </Typography>
                            <Chip 
                              label={`${(pattern.confidence * 100).toFixed(0)}% confidence`}
                              color={getConfidenceColor(pattern.confidence)}
                              size="small"
                            />
                          </Box>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Grid container spacing={2}>
                            <Grid item xs={6}>
                              <Typography variant="body2" color="text.secondary">Average Consumption</Typography>
                              <Typography variant="h6">{formatPower(pattern.average_consumption)}</Typography>
                            </Grid>
                            <Grid item xs={6}>
                              <Typography variant="body2" color="text.secondary">Peak Consumption</Typography>
                              <Typography variant="h6">{formatPower(pattern.peak_consumption)}</Typography>
                            </Grid>
                            <Grid item xs={6}>
                              <Typography variant="body2" color="text.secondary">Efficiency Score</Typography>
                              <Typography variant="h6">{(pattern.efficiency_score * 100).toFixed(1)}%</Typography>
                            </Grid>
                            <Grid item xs={6}>
                              <Typography variant="body2" color="text.secondary">Peak Hours</Typography>
                              <Typography variant="body1">
                                {pattern.peak_hours.map(h => `${h}:00`).join(', ')}
                              </Typography>
                            </Grid>
                          </Grid>
                        </AccordionDetails>
                      </Accordion>
                    ))
                  ) : (
                    <Typography color="text.secondary">No consumption patterns detected</Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={4}>
              <Card>
                <CardHeader 
                  title="Anomaly Detection" 
                  avatar={<AssessmentIcon color="warning" />}
                />
                <CardContent>
                  {anomalies.length > 0 ? (
                    <List dense>
                      {anomalies.map((anomaly, index) => (
                        <ListItem key={index} divider>
                          <ListItemText
                            primary={new Date(anomaly.timestamp).toLocaleDateString()}
                            secondary={`${anomaly.deviation.toFixed(1)}% deviation`}
                          />
                          <Chip 
                            label={anomaly.severity}
                            color={getSeverityColor(anomaly.severity)}
                            size="small"
                          />
                        </ListItem>
                      ))}
                    </List>
                  ) : (
                    <Typography color="text.secondary">No anomalies detected</Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12}>
              <Card>
                <CardHeader 
                  title="Optimization Recommendations" 
                  avatar={<LightbulbIcon color="primary" />}
                />
                <CardContent>
                  {recommendations.length > 0 ? (
                    <Grid container spacing={2}>
                      {recommendations.map((rec, index) => (
                        <Grid item xs={12} md={6} key={index}>
                          <Card variant="outlined">
                            <CardContent>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                                <Typography variant="h6">{rec.title}</Typography>
                                <Chip 
                                  label={rec.priority}
                                  color={rec.priority === 'high' ? 'error' : rec.priority === 'medium' ? 'warning' : 'info'}
                                  size="small"
                                />
                              </Box>
                              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                {rec.description}
                              </Typography>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Typography variant="body2" color="success.main">
                                  💰 {rec.potential_savings}
                                </Typography>
                                <Chip 
                                  label={`${(rec.confidence * 100).toFixed(0)}% confidence`}
                                  color={getConfidenceColor(rec.confidence)}
                                  size="small"
                                />
                              </Box>
                            </CardContent>
                          </Card>
                        </Grid>
                      ))}
                    </Grid>
                  ) : (
                    <Typography color="text.secondary">No optimization recommendations available</Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      {/* Battery Optimization Tab */}
      {activeTab === 2 && !loading && (
        <Box>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader 
                  title="Optimal SOC Range" 
                  avatar={<BatteryIcon color="primary" />}
                />
                <CardContent>
                  {batteryOptimization ? (
                    <>
                      <Box sx={{ mb: 3 }}>
                        <Typography variant="body2" color="text.secondary">Recommended Range</Typography>
                        <Typography variant="h4" color="primary">
                          {batteryOptimization.optimal_soc_range?.min || 20}% - {batteryOptimization.optimal_soc_range?.max || 80}%
                        </Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        Optimal battery management for maximum efficiency and longevity
                      </Typography>
                    </>
                  ) : (
                    <Typography color="text.secondary">No optimization data available</Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader 
                  title="Cost Savings" 
                  avatar={<AssessmentIcon color="success" />}
                />
                <CardContent>
                  {batteryOptimization?.cost_savings ? (
                    <>
                      <Typography variant="h4" color="success.main">
                        R{batteryOptimization.cost_savings.monthly_savings?.toFixed(2) || '0.00'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Estimated monthly savings with optimization
                      </Typography>
                    </>
                  ) : (
                    <Typography color="text.secondary">No cost savings data available</Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      {/* Energy Forecasting Tab */}
      {activeTab === 3 && !loading && (
        <Box>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Card>
                <CardHeader 
                  title="48-Hour Energy Forecast" 
                  avatar={<AutoGraphIcon color="primary" />}
                />
                <CardContent>
                  {energyForecasting ? (
                    <>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Model Type: {energyForecasting.model_type || 'Advanced ML'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Based on {energyForecasting.historical_data_points || 0} historical data points
                      </Typography>
                    </>
                  ) : (
                    <Typography color="text.secondary">No forecasting data available</Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      <Box sx={{ mt: 4, textAlign: 'center' }}>
        <Button 
          variant="outlined" 
          onClick={() => window.location.reload()} 
          startIcon={<AssessmentIcon />}
        >
          Refresh Analytics
        </Button>
      </Box>
    </Box>
  );
};

export default Analytics;
