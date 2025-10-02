"""
Weather Intelligence Engine - Phase 4
Integrates with existing weather correlation service for predictive alerting
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass

from .models import AlertCondition, AlertType, AlertSeverity, AlertConfiguration

logger = logging.getLogger(__name__)

@dataclass
class WeatherPrediction:
    """Weather-based energy prediction"""
    timestamp: datetime
    predicted_solar_power: float  # kW
    predicted_deficit: float  # kW
    confidence: float  # 0.0 to 1.0
    weather_factors: Dict[str, float]
    alert_recommended: bool

@dataclass
class WeatherAlert:
    """Weather-based alert recommendation"""
    alert_type: str
    severity: AlertSeverity
    description: str
    time_to_impact: float  # hours
    confidence: float
    recommended_actions: List[str]

class WeatherIntelligenceEngine:
    """
    Advanced weather intelligence for predictive alerting
    Integrates with existing weather_correlator.py
    """
    
    def __init__(self):
        self.weather_correlator = None
        self.prediction_cache: Dict[str, WeatherPrediction] = {}
        self.alert_history: List[WeatherAlert] = []
        self.learning_enabled = True
        
    async def initialize(self):
        """Initialize weather intelligence with existing correlator"""
        try:
            # Import existing weather correlator
            from ..analytics.weather_correlator import weather_analyzer
            self.weather_correlator = weather_analyzer
            logger.info("Weather intelligence engine initialized with existing correlator")
        except ImportError as e:
            logger.error(f"Failed to import weather correlator: {e}")
            self.weather_correlator = None
    
    async def predict_energy_deficit(self, config: AlertConfiguration, 
                                   hours_ahead: int = 2) -> List[WeatherPrediction]:
        """
        Predict energy deficits based on weather forecasts
        
        Args:
            config: Alert configuration
            hours_ahead: Hours to predict ahead
            
        Returns:
            List of weather predictions
        """
        if not self.weather_correlator:
            await self.initialize()
            if not self.weather_correlator:
                return []
        
        try:
            # Get weather forecast from existing service
            weather_forecasts = await self.weather_correlator.get_weather_forecast(days=2)
            
            if not weather_forecasts:
                logger.warning("No weather forecast data available")
                return []
            
            predictions = []
            current_time = datetime.now()
            
            # Process forecast data for predictions
            for forecast in weather_forecasts:
                if forecast.timestamp <= current_time:
                    continue
                    
                time_diff = (forecast.timestamp - current_time).total_seconds() / 3600
                if time_diff > hours_ahead:
                    break
                
                # Predict solar power based on weather
                predicted_solar = self._predict_solar_power(forecast)
                
                # Estimate consumption (would use historical patterns)
                predicted_consumption = self._estimate_consumption(forecast.timestamp)
                
                # Calculate predicted deficit
                predicted_deficit = max(0, predicted_consumption - predicted_solar)
                
                # Calculate confidence based on weather conditions
                confidence = self._calculate_prediction_confidence(forecast)
                
                # Check if deficit warrants alert
                alert_recommended = (
                    predicted_deficit >= config.energy_thresholds.deficit_threshold_kw and
                    confidence >= 0.6
                )
                
                prediction = WeatherPrediction(
                    timestamp=forecast.timestamp,
                    predicted_solar_power=predicted_solar,
                    predicted_deficit=predicted_deficit,
                    confidence=confidence,
                    weather_factors={
                        'cloud_cover': forecast.cloud_cover,
                        'temperature': forecast.temperature,
                        'solar_radiation': forecast.solar_radiation,
                        'condition': forecast.weather_condition
                    },
                    alert_recommended=alert_recommended
                )
                
                predictions.append(prediction)
                
                # Cache prediction
                cache_key = f"{forecast.timestamp.isoformat()}"
                self.prediction_cache[cache_key] = prediction
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting energy deficit: {e}")
            return []
    
    def _predict_solar_power(self, weather_forecast) -> float:
        """Predict solar power based on weather forecast"""
        try:
            # Base prediction on solar radiation and weather conditions
            base_power = (weather_forecast.solar_radiation / 1000) * 5.0  # 5kW system
            
            # Apply weather condition factors
            condition_factors = {
                'clear': 1.0,
                'clouds': 0.7,
                'rain': 0.3,
                'drizzle': 0.4,
                'thunderstorm': 0.2,
                'snow': 0.1,
                'mist': 0.6,
                'fog': 0.4
            }
            
            condition_factor = condition_factors.get(weather_forecast.weather_condition, 0.5)
            
            # Apply cloud cover reduction
            cloud_factor = 1 - (weather_forecast.cloud_cover / 100) * 0.8
            
            # Temperature efficiency (panels less efficient when hot)
            temp_factor = 1 - max(0, (weather_forecast.temperature - 25) * 0.004)
            
            predicted_power = base_power * condition_factor * cloud_factor * temp_factor
            
            return max(0, predicted_power)
            
        except Exception as e:
            logger.error(f"Error predicting solar power: {e}")
            return 0.0
    
    def _estimate_consumption(self, timestamp: datetime) -> float:
        """Estimate consumption based on time patterns"""
        # Simple time-based consumption estimation
        # In reality, this would use ML models based on historical data
        hour = timestamp.hour
        
        if 6 <= hour <= 8:  # Morning peak
            return 2.5
        elif 9 <= hour <= 16:  # Day time
            return 1.8
        elif 17 <= hour <= 20:  # Evening peak
            return 3.2
        elif 21 <= hour <= 23:  # Night
            return 2.0
        else:  # Late night/early morning
            return 1.5
    
    def _calculate_prediction_confidence(self, weather_forecast) -> float:
        """Calculate confidence in weather prediction"""
        confidence = 0.7  # Base confidence
        
        # Adjust based on weather conditions
        if weather_forecast.weather_condition in ['clear', 'clouds']:
            confidence += 0.2
        elif weather_forecast.weather_condition in ['rain', 'thunderstorm']:
            confidence -= 0.1
        
        # Adjust based on cloud cover consistency
        if weather_forecast.cloud_cover <= 20 or weather_forecast.cloud_cover >= 80:
            confidence += 0.1  # Clear or very cloudy conditions are more predictable
        
        return max(0.3, min(0.95, confidence))
    
    async def generate_weather_alerts(self, config: AlertConfiguration) -> List[WeatherAlert]:
        """
        Generate weather-based alert recommendations
        
        Args:
            config: Alert configuration
            
        Returns:
            List of weather alerts
        """
        try:
            # Get energy deficit predictions
            predictions = await self.predict_energy_deficit(config, hours_ahead=6)
            
            alerts = []
            current_time = datetime.now()
            
            for prediction in predictions:
                if not prediction.alert_recommended:
                    continue
                
                time_to_impact = (prediction.timestamp - current_time).total_seconds() / 3600
                
                # Determine alert severity based on deficit magnitude and confidence
                if prediction.predicted_deficit > config.energy_thresholds.deficit_threshold_kw * 2:
                    severity = AlertSeverity.HIGH
                elif prediction.predicted_deficit > config.energy_thresholds.deficit_threshold_kw:
                    severity = AlertSeverity.MEDIUM
                else:
                    severity = AlertSeverity.LOW
                
                # Adjust severity based on confidence
                if prediction.confidence < 0.6:
                    severity = AlertSeverity.LOW
                
                # Generate alert description
                description = self._generate_weather_alert_description(prediction, time_to_impact)
                
                # Generate recommended actions
                actions = self._generate_recommended_actions(prediction, config)
                
                alert = WeatherAlert(
                    alert_type="weather_energy_deficit",
                    severity=severity,
                    description=description,
                    time_to_impact=time_to_impact,
                    confidence=prediction.confidence,
                    recommended_actions=actions
                )
                
                alerts.append(alert)
            
            # Store alerts in history for learning
            self.alert_history.extend(alerts)
            
            # Limit history size
            if len(self.alert_history) > 100:
                self.alert_history = self.alert_history[-100:]
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error generating weather alerts: {e}")
            return []
    
    def _generate_weather_alert_description(self, prediction: WeatherPrediction, 
                                          time_to_impact: float) -> str:
        """Generate human-readable weather alert description"""
        condition = prediction.weather_factors.get('condition', 'unknown')
        cloud_cover = prediction.weather_factors.get('cloud_cover', 0)
        deficit = prediction.predicted_deficit
        
        description = f"Weather forecast indicates potential energy deficit of {deficit:.2f}kW "
        description += f"in {time_to_impact:.1f} hours due to {condition} conditions "
        description += f"with {cloud_cover:.0f}% cloud cover."
        
        return description
    
    def _generate_recommended_actions(self, prediction: WeatherPrediction, 
                                    config: AlertConfiguration) -> List[str]:
        """Generate recommended actions based on prediction"""
        actions = []
        
        deficit = prediction.predicted_deficit
        condition = prediction.weather_factors.get('condition', 'unknown')
        
        # Battery preparation actions
        if deficit > config.energy_thresholds.deficit_threshold_kw:
            actions.append("Ensure battery is fully charged before deficit period")
            actions.append("Consider reducing non-essential electrical usage")
        
        # Weather-specific actions
        if condition in ['rain', 'thunderstorm', 'clouds']:
            actions.append("Prepare for reduced solar generation")
            if deficit > 2.0:
                actions.append("Consider backup power options")
        
        # Timing-based actions
        time_to_impact = (prediction.timestamp - datetime.now()).total_seconds() / 3600
        if time_to_impact < 2:
            actions.append("Take immediate action - deficit expected soon")
        elif time_to_impact < 6:
            actions.append("Prepare for upcoming energy deficit")
        
        return actions
    
    async def analyze_weather_patterns(self, days_back: int = 30) -> Dict:
        """
        Analyze historical weather patterns for insights
        
        Args:
            days_back: Days of history to analyze
            
        Returns:
            Dictionary of weather pattern insights
        """
        if not self.weather_correlator:
            await self.initialize()
            if not self.weather_correlator:
                return {}
        
        try:
            # This would integrate with historical weather data analysis
            # For now, return simulated insights
            
            insights = {
                'average_cloud_cover': 45.0,
                'rainy_days_percentage': 15.0,
                'peak_solar_hours': [10, 11, 12, 13, 14],
                'deficit_prone_conditions': ['cloudy', 'rain', 'overcast'],
                'best_solar_conditions': ['clear', 'partly_cloudy'],
                'seasonal_trends': {
                    'summer': {'avg_generation': 6.2, 'deficit_days': 8},
                    'winter': {'avg_generation': 3.8, 'deficit_days': 18},
                    'autumn': {'avg_generation': 4.8, 'deficit_days': 12},
                    'spring': {'avg_generation': 5.5, 'deficit_days': 10}
                }
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error analyzing weather patterns: {e}")
            return {}
    
    def learn_from_alert_outcomes(self, alert_id: str, actual_outcome: Dict):
        """
        Learn from alert outcomes to improve future predictions
        
        Args:
            alert_id: ID of the alert to learn from
            actual_outcome: Actual energy data and outcomes
        """
        if not self.learning_enabled:
            return
        
        try:
            # This would implement machine learning to improve predictions
            # For now, just log the outcome for future development
            logger.info(f"Learning from alert outcome: {alert_id}")
            
            # In a full implementation, this would:
            # 1. Compare predicted vs actual deficit
            # 2. Analyze weather forecast accuracy
            # 3. Adjust prediction models
            # 4. Update confidence factors
            # 5. Improve alert thresholds
            
            # Placeholder for ML learning logic
            actual_deficit = actual_outcome.get('actual_deficit', 0)
            predicted_deficit = actual_outcome.get('predicted_deficit', 0)
            
            if abs(actual_deficit - predicted_deficit) > 0.5:
                logger.warning(f"Prediction accuracy issue: predicted {predicted_deficit}, actual {actual_deficit}")
            
        except Exception as e:
            logger.error(f"Error in learning from alert outcomes: {e}")
    
    async def get_realtime_weather_impact(self) -> Dict:
        """Get real-time weather impact on solar generation"""
        if not self.weather_correlator:
            await self.initialize()
            if not self.weather_correlator:
                return {}
        
        try:
            # Get current weather data
            current_weather = await self.weather_correlator.get_enhanced_weather_data()
            
            if not current_weather:
                return {}
            
            # Calculate current impact
            impact = {
                'timestamp': datetime.now().isoformat(),
                'cloud_cover': current_weather.cloud_cover,
                'solar_radiation': current_weather.solar_radiation,
                'temperature': current_weather.temperature,
                'weather_condition': current_weather.weather_condition,
                'generation_impact_percentage': self._calculate_generation_impact(current_weather),
                'deficit_risk': self._calculate_deficit_risk(current_weather)
            }
            
            return impact
            
        except Exception as e:
            logger.error(f"Error getting real-time weather impact: {e}")
            return {}
    
    def _calculate_generation_impact(self, weather_data) -> float:
        """Calculate percentage impact on solar generation"""
        try:
            # Base impact from cloud cover
            cloud_impact = weather_data.cloud_cover * 0.8  # Up to 80% reduction
            
            # Weather condition impact
            condition_impacts = {
                'clear': 0,
                'clouds': 15,
                'rain': 60,
                'drizzle': 45,
                'thunderstorm': 70,
                'snow': 80,
                'mist': 25,
                'fog': 35
            }
            
            condition_impact = condition_impacts.get(weather_data.weather_condition, 30)
            
            # Temperature impact (efficiency loss when hot)
            temp_impact = max(0, (weather_data.temperature - 25) * 2)  # 2% per degree above 25°C
            
            total_impact = min(90, cloud_impact + condition_impact + temp_impact)
            return round(total_impact, 1)
            
        except Exception as e:
            logger.error(f"Error calculating generation impact: {e}")
            return 0.0
    
    def _calculate_deficit_risk(self, weather_data) -> str:
        """Calculate deficit risk level based on weather"""
        try:
            generation_impact = self._calculate_generation_impact(weather_data)
            
            if generation_impact > 60:
                return "high"
            elif generation_impact > 30:
                return "medium"
            elif generation_impact > 10:
                return "low"
            else:
                return "minimal"
                
        except Exception as e:
            logger.error(f"Error calculating deficit risk: {e}")
            return "unknown"

# Global weather intelligence instance
weather_intelligence = WeatherIntelligenceEngine()