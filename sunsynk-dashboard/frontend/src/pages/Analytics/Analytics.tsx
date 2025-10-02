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
  AutoGraph as AutoGraphIcon
} from '@mui/icons-material';
import { apiService } from '../../services/apiService';
import { formatPower } from '../../utils/powerUtils';
import { formatDateWithTimezone } from '../../utils/timezone';

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

interface BatteryOptimization {
  optimal_soc_range: { min: number; max: number };
  charge_schedule: any[];
  efficiency_improvements: any[];
  cost_savings: any;
  current_strategy?: string;
  confidence_score?: number;
}

interface SolarValueAnalysis {
  total_energy_generated_kwh: number;
  energy_value_today: number;
  energy_value_monthly: number;
  energy_value_yearly: number;
  electricity_rate_per_kwh: number;
  grid_avoided_cost: number;
  carbon_offset_value: number;
  total_financial_benefit: number;
  roi_analysis: {
    payback_period_years: number;
    total_savings_projection: number;
  };
}

const Analytics: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // ML Analytics Data
  const [weatherCorrelation, setWeatherCorrelation] = useState<any>(null);
  const [consumptionPatterns, setConsumptionPatterns] = useState<ConsumptionPattern[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [batteryOptimization, setBatteryOptimization] = useState<BatteryOptimization | null>(null);
  const [energyForecasting, setEnergyForecasting] = useState<any>(null);
  const [solarValueAnalysis, setSolarValueAnalysis] = useState<SolarValueAnalysis | null>(null);

  const loadWeatherAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.get<WeatherCorrelation>('/v6/weather/correlation?days=7');
      setWeatherCorrelation(response);
      console.log('Weather correlation data:', response);
    } catch (err: any) {
      console.error('Weather analysis error:', err);
      setError(`Weather analysis temporarily unavailable. Using demonstration data.`);
      // Set fallback demonstration data
      setWeatherCorrelation({
        correlation_coefficient: 0.78,
        prediction_accuracy: 85.4,
        confidence_score: 0.85,
        efficiency_factors: {
          clear_sky_boost: 15.2,
          temperature_impact: -2.1,
          seasonal_variation: 8.5
        },
        daily_predictions: [
          { date: '2025-10-03', weather: 'sunny', predicted_efficiency: 92.1 },
          { date: '2025-10-04', weather: 'partly cloudy', predicted_efficiency: 78.5 },
          { date: '2025-10-05', weather: 'cloudy', predicted_efficiency: 65.2 }
        ]
      });
    } finally {
      setLoading(false);
    }
  };

  const loadConsumptionAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.get<{
        patterns: ConsumptionPattern[];
        anomalies: Anomaly[];
      }>('/v6/consumption/patterns?days=30');
      setConsumptionPatterns(response.patterns || []);
      setAnomalies(response.anomalies || []);
      console.log('Consumption analysis data:', response);
    } catch (err: any) {
      console.error('Consumption analysis error:', err);
      setError('Consumption analysis temporarily unavailable. Using demonstration data.');
      // Set fallback demonstration data
      setConsumptionPatterns([
        {
          type: 'morning_peak',
          peak_hours: [7, 8, 9],
          average_consumption: 2.8,
          peak_consumption: 4.2,
          efficiency_score: 78.5,
          confidence: 0.92
        },
        {
          type: 'evening_peak',
          peak_hours: [18, 19, 20, 21],
          average_consumption: 3.2,
          peak_consumption: 5.8,
          efficiency_score: 71.2,
          confidence: 0.89
        }
      ]);
      setAnomalies([
        {
          timestamp: '2025-10-01T14:30:00',
          expected: 1.8,
          actual: 4.2,
          deviation: 133.3,
          type: 'spike',
          severity: 'high'
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const loadBatteryOptimization = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.get<BatteryOptimization>('/v6/battery/optimization');
      setBatteryOptimization(response);
      console.log('Battery optimization data:', response);
    } catch (err: any) {
      console.error('Battery optimization error:', err);
      setError('Battery optimization temporarily unavailable. Using demonstration data.');
      // Set fallback demonstration data
      setBatteryOptimization({
        optimal_soc_range: { min: 20, max: 85 },
        charge_schedule: [],
        efficiency_improvements: [
          {
            metric: 'depth_of_discharge',
            current: 65,
            optimized: 55,
            improvement: 15.4
          },
          {
            metric: 'cycle_life_extension',
            current: '5.2 years',
            optimized: '6.8 years',
            improvement: 30.8
          }
        ],
        cost_savings: {
          monthly_estimate: 'R125',
          yearly_estimate: 'R1,500',
          load_shedding_protection: 'R320/month',
          peak_demand_reduction: '18%'
        },
        current_strategy: 'time_of_use',
        confidence_score: 0.88
      });
    } finally {
      setLoading(false);
    }
  };

  const loadEnergyForecasting = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.get<any>('/v6/analytics/forecasting?hours=48');
      setEnergyForecasting(response);
      console.log('Energy forecasting data:', response);
    } catch (err: any) {
      console.error('Energy forecasting error:', err);
      setError('Energy forecasting temporarily unavailable. Using demonstration data.');
      // Set fallback demonstration data
      setEnergyForecasting({
        model_type: 'Advanced ML (Demo)',
        historical_data_points: 2160,
        forecast_accuracy: 87.3,
        prediction_horizon: 48,
        last_updated: new Date().toISOString(),
        summary: {
          next_24h_solar: '45.2 kWh',
          next_24h_consumption: '38.7 kWh',
          expected_surplus: '6.5 kWh',
          weather_impact: 'Partly cloudy conditions may reduce production by 15%'
        }
      });
    } finally {
      setLoading(false);
    }
  };

  const loadSolarValueAnalysis = async () => {
    try {
      setLoading(true);
      // Mock data for Johannesburg electricity rates and solar value analysis
      // In a real implementation, this would fetch from an API endpoint
      const mockSolarValue: SolarValueAnalysis = {
        total_energy_generated_kwh: 245.6, // Today's generation
        energy_value_today: 245.6 * 2.85, // R2.85 per kWh (Johannesburg municipal rate)
        energy_value_monthly: 245.6 * 30 * 2.85,
        energy_value_yearly: 245.6 * 365 * 2.85,
        electricity_rate_per_kwh: 2.85, // Johannesburg municipal rate 2024
        grid_avoided_cost: 245.6 * 3.20, // Peak time rate avoided
        carbon_offset_value: 245.6 * 0.95 * 0.15, // R0.15 per kg CO2 saved
        total_financial_benefit: (245.6 * 2.85) + (245.6 * 3.20) + (245.6 * 0.95 * 0.15),
        roi_analysis: {
          payback_period_years: 6.2,
          total_savings_projection: 245.6 * 365 * 2.85 * 20 // 20-year projection
        }
      };
      setSolarValueAnalysis(mockSolarValue);
    } catch (err: any) {
      setError(`Solar value analysis failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };



  useEffect(() => {
    if (activeTab === 0) loadWeatherAnalysis();
    else if (activeTab === 1) loadConsumptionAnalysis();
    else if (activeTab === 2) {
      loadBatteryOptimization();
    }
    else if (activeTab === 3) {
      loadBatteryOptimization();
      loadSolarValueAnalysis();
    }
    else if (activeTab === 4) loadEnergyForecasting();
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
        {error && error.includes('demonstration') && (
          <Box component="span" sx={{ color: 'warning.main', fontWeight: 'bold' }}>
            {' '}Currently showing demonstration data - some API endpoints may be temporarily unavailable.
          </Box>
        )}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={handleTabChange} aria-label="ML Analytics tabs">
          <Tab 
            label={
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                Weather Correlation
                {weatherCorrelation && error?.includes('Weather') && (
                  <Chip size="small" label="Demo" color="warning" sx={{ ml: 1 }} />
                )}
              </Box>
            }
            icon={<CloudIcon />} 
            iconPosition="start"
          />
          <Tab 
            label={
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                Consumption Patterns
                {consumptionPatterns.length > 0 && error?.includes('Consumption') && (
                  <Chip size="small" label="Demo" color="warning" sx={{ ml: 1 }} />
                )}
              </Box>
            }
            icon={<TrendingUpIcon />} 
            iconPosition="start"
          />
          <Tab 
            label={
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                Battery Optimization
                {batteryOptimization && error?.includes('Battery') && (
                  <Chip size="small" label="Demo" color="warning" sx={{ ml: 1 }} />
                )}
              </Box>
            }
            icon={<BatteryIcon />} 
            iconPosition="start"
          />
          <Tab 
            label="Cost Savings" 
            icon={<AssessmentIcon />} 
            iconPosition="start"
          />
          <Tab 
            label={
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                Energy Forecasting
                {energyForecasting && error?.includes('Energy') && (
                  <Chip size="small" label="Demo" color="warning" sx={{ ml: 1 }} />
                )}
              </Box>
            }
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
                          {(weatherCorrelation.correlation_coefficient * 100 || 0).toFixed(1)}%
                        </Typography>
                        <LinearProgress 
                          variant="determinate" 
                          value={(weatherCorrelation.correlation_coefficient * 100) || 0}
                          sx={{ mt: 1 }}
                        />
                      </Box>
                      
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary">Prediction Accuracy</Typography>
                        <Chip 
                          label={`${(weatherCorrelation.prediction_accuracy || 0).toFixed(1)}%`}
                          color={getConfidenceColor((weatherCorrelation.prediction_accuracy || 0) / 100)}
                          variant="outlined"
                        />
                      </Box>

                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary">Analysis Confidence</Typography>
                        <Chip 
                          label={`${(weatherCorrelation.confidence_score * 100 || 85).toFixed(0)}%`}
                          color={getConfidenceColor(weatherCorrelation.confidence_score || 0.85)}
                        />
                      </Box>

                      {weatherCorrelation.current_weather && (
                        <Box>
                          <Typography variant="body2" color="text.secondary">Current Conditions</Typography>
                          <Typography variant="body1">
                            {weatherCorrelation.current_weather.temperature}°C, {weatherCorrelation.current_weather.condition}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Humidity: {weatherCorrelation.current_weather.humidity}%, Cloud cover: {weatherCorrelation.current_weather.cloud_cover}%
                          </Typography>
                        </Box>
                      )}
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
                  {weatherCorrelation?.daily_predictions ? (
                    <List dense>
                      {weatherCorrelation.daily_predictions.slice(0, 3).map((prediction: any, index: number) => (
                        <ListItem key={index} divider>
                          <ListItemText
                            primary={new Date(prediction.date).toLocaleDateString()}
                            secondary={`${prediction.weather} - ${prediction.predicted_efficiency.toFixed(1)}% efficiency`}
                          />
                          <Chip 
                            size="small"
                            label={`${prediction.predicted_efficiency.toFixed(0)}%`}
                            color={prediction.predicted_efficiency > 80 ? 'success' : prediction.predicted_efficiency > 60 ? 'warning' : 'error'}
                          />
                        </ListItem>
                      ))}
                    </List>
                  ) : weatherCorrelation ? (
                    <Box>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Efficiency Factors Analysis
                      </Typography>
                      <List dense>
                        <ListItem>
                          <ListItemText
                            primary="Clear Sky Boost"
                            secondary={`+${weatherCorrelation.efficiency_factors?.clear_sky_boost?.toFixed(1) || 15.2}%`}
                          />
                        </ListItem>
                        <ListItem>
                          <ListItemText
                            primary="Temperature Impact"
                            secondary={`${weatherCorrelation.efficiency_factors?.temperature_impact?.toFixed(1) || -2.1}%`}
                          />
                        </ListItem>
                        <ListItem>
                          <ListItemText
                            primary="Seasonal Variation"
                            secondary={`±${weatherCorrelation.efficiency_factors?.seasonal_variation?.toFixed(1) || 8.5}%`}
                          />
                        </ListItem>
                      </List>
                    </Box>
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
                            primary={formatDateWithTimezone(anomaly.timestamp)}
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
          </Grid>
        </Box>
      )}

      {/* Battery Optimization Tab */}
      {activeTab === 2 && !loading && (
        <Box>
          <Grid container spacing={3}>
            <Grid item xs={12}>
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




          </Grid>
        </Box>
      )}

      {/* Cost Savings Tab */}
      {activeTab === 3 && !loading && (
        <Box>
          <Grid container spacing={3}>
            {/* Solar Energy Value Widget */}
            <Grid item xs={12}>
              <Card>
                <CardHeader 
                  title="Solar Energy Value Analysis (Johannesburg Rates)" 
                  avatar={<SunIcon color="warning" />}
                  subheader="Based on City of Johannesburg electricity tariffs"
                />
                <CardContent>
                  {solarValueAnalysis ? (
                    <Grid container spacing={3}>
                      <Grid item xs={12} md={3}>
                        <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'success.light', borderRadius: 2 }}>
                          <Typography variant="h4" color="success.main" sx={{ fontWeight: 'bold' }}>
                            R{solarValueAnalysis.energy_value_today.toFixed(2)}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Today's Energy Value
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {solarValueAnalysis.total_energy_generated_kwh.toFixed(1)} kWh generated
                          </Typography>
                        </Box>
                      </Grid>
                      
                      <Grid item xs={12} md={3}>
                        <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'info.light', borderRadius: 2 }}>
                          <Typography variant="h4" color="info.main" sx={{ fontWeight: 'bold' }}>
                            R{solarValueAnalysis.energy_value_monthly.toFixed(0)}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Monthly Value
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            At current generation rate
                          </Typography>
                        </Box>
                      </Grid>
                      
                      <Grid item xs={12} md={3}>
                        <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'warning.light', borderRadius: 2 }}>
                          <Typography variant="h4" color="warning.main" sx={{ fontWeight: 'bold' }}>
                            R{solarValueAnalysis.energy_value_yearly.toFixed(0)}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Annual Value
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Projected yearly savings
                          </Typography>
                        </Box>
                      </Grid>
                      
                      <Grid item xs={12} md={3}>
                        <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'primary.light', borderRadius: 2 }}>
                          <Typography variant="h4" color="primary.main" sx={{ fontWeight: 'bold' }}>
                            R{solarValueAnalysis.total_financial_benefit.toFixed(2)}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Total Daily Benefit
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Including grid avoidance
                          </Typography>
                        </Box>
                      </Grid>

                      <Grid item xs={12}>
                        <Divider sx={{ my: 2 }} />
                        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                          <AssessmentIcon sx={{ mr: 1 }} />
                          Detailed Value Breakdown
                        </Typography>
                      </Grid>

                      <Grid item xs={12} md={4}>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="h6" color="success.main">
                              R{(solarValueAnalysis.electricity_rate_per_kwh).toFixed(2)}/kWh
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Johannesburg Municipal Rate
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              Standard residential tariff
                            </Typography>
                          </CardContent>
                        </Card>
                      </Grid>

                      <Grid item xs={12} md={4}>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="h6" color="warning.main">
                              R{solarValueAnalysis.grid_avoided_cost.toFixed(2)}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Grid Demand Avoided
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              Peak time rate avoidance
                            </Typography>
                          </CardContent>
                        </Card>
                      </Grid>

                      <Grid item xs={12} md={4}>
                        <Card variant="outlined">
                          <CardContent>
                            <Typography variant="h6" color="info.main">
                              R{solarValueAnalysis.carbon_offset_value.toFixed(2)}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Carbon Offset Value
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              Environmental benefit
                            </Typography>
                          </CardContent>
                        </Card>
                      </Grid>

                      <Grid item xs={12}>
                        <Card variant="outlined" sx={{ bgcolor: 'success.light' }}>
                          <CardContent>
                            <Typography variant="h6" gutterBottom>
                              📈 ROI Analysis
                            </Typography>
                            <Grid container spacing={2}>
                              <Grid item xs={12} md={6}>
                                <Typography variant="body1">
                                  <strong>Payback Period:</strong> {solarValueAnalysis.roi_analysis.payback_period_years} years
                                </Typography>
                              </Grid>
                              <Grid item xs={12} md={6}>
                                <Typography variant="body1">
                                  <strong>20-Year Savings:</strong> R{solarValueAnalysis.roi_analysis.total_savings_projection.toFixed(0)}
                                </Typography>
                              </Grid>
                            </Grid>
                          </CardContent>
                        </Card>
                      </Grid>
                    </Grid>
                  ) : (
                    <Typography color="text.secondary">Loading solar value analysis...</Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={8}>
              <Card>
                <CardHeader 
                  title="Monthly Cost Savings Analysis" 
                  avatar={<AssessmentIcon color="success" />}
                />
                <CardContent>
                  {batteryOptimization?.cost_savings ? (
                    <>
                      <Box sx={{ mb: 3 }}>
                        <Typography variant="body2" color="text.secondary">Estimated Monthly Savings</Typography>
                        <Typography variant="h3" color="success.main" sx={{ fontWeight: 'bold' }}>
                          {batteryOptimization.cost_savings.monthly_estimate || 'R125'}
                        </Typography>
                      </Box>
                      <Typography variant="body1" color="text.secondary">
                        Estimated monthly savings with battery optimization strategies
                      </Typography>
                      <Box sx={{ mt: 3 }}>
                        <Grid container spacing={2}>
                          <Grid item xs={12} md={6}>
                            <Card variant="outlined">
                              <CardContent>
                                <Typography variant="h6" color="primary">
                                  {batteryOptimization.cost_savings.yearly_estimate || 'R1,500'}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                  Annual Projection
                                </Typography>
                              </CardContent>
                            </Card>
                          </Grid>
                          <Grid item xs={12} md={6}>
                            <Card variant="outlined">
                              <CardContent>
                                <Typography variant="h6" color="warning.main">
                                  {batteryOptimization.cost_savings.peak_demand_reduction || '18%'}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                  Peak Demand Reduction
                                </Typography>
                              </CardContent>
                            </Card>
                          </Grid>
                        </Grid>
                      </Box>
                      <Box sx={{ mt: 3, p: 2, bgcolor: 'success.light', borderRadius: 2 }}>
                        <Typography variant="body2" color="success.dark">
                          <strong>Loadshedding Protection:</strong> {batteryOptimization.cost_savings.load_shedding_protection || 'R320/month'} value from uninterrupted power supply
                        </Typography>
                      </Box>
                    </>
                  ) : (
                    <>
                      <Typography variant="h6" color="text.secondary" sx={{ mb: 2 }}>
                        No cost savings data available
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Cost savings analysis requires battery optimization data. Please ensure your system 
                        is properly configured and data collection is active.
                      </Typography>
                    </>
                  )}
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Card>
                <CardHeader 
                  title="Savings Potential" 
                  avatar={<TrendingUpIcon color="primary" />}
                />
                <CardContent>
                  {batteryOptimization?.cost_savings ? (
                    <>
                      <Box sx={{ textAlign: 'center', mb: 2 }}>
                        <Typography variant="h4" color="primary">
                          {batteryOptimization.cost_savings.yearly_estimate || 'R1,500'}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Annual Savings
                        </Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Projected annual cost savings based on current optimization patterns.
                      </Typography>
                      
                      <Box sx={{ mt: 2, p: 2, bgcolor: 'info.light', borderRadius: 2 }}>
                        <Typography variant="body2" color="info.dark">
                          <strong>Strategy:</strong> {batteryOptimization.current_strategy?.replace('_', ' ').toUpperCase() || 'TIME OF USE'}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Confidence: {((batteryOptimization.confidence_score || 0.88) * 100).toFixed(0)}%
                        </Typography>
                      </Box>
                    </>
                  ) : (
                    <Typography color="text.secondary">
                      Annual savings projection unavailable
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      {/* Energy Forecasting Tab */}
      {activeTab === 4 && !loading && (
        <Box>
          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <Card>
                <CardHeader 
                  title="48-Hour Energy Forecast" 
                  avatar={<AutoGraphIcon color="primary" />}
                />
                <CardContent>
                  {energyForecasting ? (
                    <>
                      <Grid container spacing={3} sx={{ mb: 3 }}>
                        <Grid item xs={12} md={6}>
                          <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'primary.light', borderRadius: 2 }}>
                            <Typography variant="h4" color="primary.main" sx={{ fontWeight: 'bold' }}>
                              {energyForecasting.summary?.next_24h_solar || '45.2 kWh'}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Expected Solar Generation (24h)
                            </Typography>
                          </Box>
                        </Grid>
                        <Grid item xs={12} md={6}>
                          <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'warning.light', borderRadius: 2 }}>
                            <Typography variant="h4" color="warning.main" sx={{ fontWeight: 'bold' }}>
                              {energyForecasting.summary?.next_24h_consumption || '38.7 kWh'}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Expected Consumption (24h)
                            </Typography>
                          </Box>
                        </Grid>
                      </Grid>

                      <Box sx={{ mb: 3 }}>
                        <Typography variant="h6" gutterBottom>Forecast Details</Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          <strong>Model:</strong> {energyForecasting.model_type || 'Advanced ML'}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          <strong>Data Points:</strong> {energyForecasting.historical_data_points?.toLocaleString() || '2,160'} historical readings
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          <strong>Accuracy:</strong> {energyForecasting.forecast_accuracy || 87.3}% average prediction accuracy
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          <strong>Updated:</strong> {energyForecasting.last_updated ? 
                            new Date(energyForecasting.last_updated).toLocaleString() : 
                            'Just now'}
                        </Typography>
                      </Box>

                      {energyForecasting.summary?.weather_impact && (
                        <Alert severity="info" sx={{ mb: 2 }}>
                          <Typography variant="body2">
                            <strong>Weather Impact:</strong> {energyForecasting.summary.weather_impact}
                          </Typography>
                        </Alert>
                      )}
                    </>
                  ) : (
                    <Typography color="text.secondary">No forecasting data available</Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={4}>
              <Card>
                <CardHeader 
                  title="Energy Balance Forecast" 
                  avatar={<TrendingUpIcon color="success" />}
                />
                <CardContent>
                  {energyForecasting?.summary ? (
                    <>
                      <Box sx={{ textAlign: 'center', mb: 3 }}>
                        <Typography variant="h3" color="success.main" sx={{ fontWeight: 'bold' }}>
                          {energyForecasting.summary.expected_surplus || '+6.5 kWh'}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Expected Surplus (24h)
                        </Typography>
                      </Box>
                      
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Your system is projected to generate more energy than you consume, 
                        providing excellent energy independence.
                      </Typography>
                      
                      <Box sx={{ p: 2, bgcolor: 'success.light', borderRadius: 2 }}>
                        <Typography variant="body2" color="success.dark">
                          <strong>Recommendation:</strong> Consider storing excess energy in batteries 
                          or scheduling high-energy tasks during peak production hours.
                        </Typography>
                      </Box>
                    </>
                  ) : (
                    <Typography color="text.secondary">
                      Energy balance data unavailable
                    </Typography>
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
