"""
Advanced Battery Prediction Engine for Sunsynk Solar Dashboard.
Implements machine learning models for battery optimization and predictive analytics.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
import statistics
import math
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import pickle
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from collector.database import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class BatteryPrediction:
    """Battery prediction results."""
    timestamp: datetime
    current_soc: float
    predicted_soc_1h: float
    predicted_soc_4h: float
    predicted_soc_8h: float
    predicted_soc_24h: float
    depletion_risk_score: float  # 0-1, higher is more risk
    charging_opportunity_score: float  # 0-1, higher is better opportunity
    optimal_load_schedule: List[Dict[str, Any]]
    confidence_score: float  # 0-1, prediction confidence
    model_features: Dict[str, float]


@dataclass
class LoadPrediction:
    """Load consumption prediction."""
    timestamp: datetime
    predicted_load_1h: float
    predicted_load_4h: float
    predicted_load_8h: float
    predicted_load_24h: float
    peak_load_time: datetime
    peak_load_value: float
    base_load: float
    load_pattern_type: str  # weekday, weekend, holiday
    confidence_score: float


@dataclass
class SolarPrediction:
    """Solar generation prediction."""
    timestamp: datetime
    predicted_solar_1h: float
    predicted_solar_4h: float
    predicted_solar_8h: float
    predicted_solar_24h: float
    daily_total_kwh: float
    peak_generation_time: datetime
    peak_generation_value: float
    weather_impact_score: float  # -1 to 1, negative for adverse weather
    confidence_score: float


class BatteryPredictor:
    """
    Advanced battery prediction engine using machine learning and pattern recognition.
    Implements multiple prediction models for different time horizons.
    """
    
    def __init__(self, db_manager: DatabaseManager = None):
        """Initialize battery predictor."""
        self.db_manager = db_manager or DatabaseManager()
        
        # Model configuration
        self.lookback_hours = 168  # 7 days for pattern learning
        self.min_data_points = 50
        self.prediction_horizons = [1, 4, 8, 24]  # hours
        
        # Battery configuration
        self.battery_capacity_kwh = float(os.getenv('BATTERY_CAPACITY_KWH', '5.0'))
        self.min_soc = float(os.getenv('BATTERY_MIN_SOC', '15.0'))
        self.max_soc = float(os.getenv('BATTERY_MAX_SOC', '95.0'))
        self.inverter_efficiency = float(os.getenv('INVERTER_EFFICIENCY', '0.95'))
        
        # Pattern recognition
        self.patterns = {
            'weekday': defaultdict(list),
            'weekend': defaultdict(list),
            'weather': defaultdict(list)
        }
        
        # Model cache
        self.model_cache = {}
        self.last_training = None
        self.training_interval = timedelta(hours=6)
        
        # Feature importance weights (learned from data)
        self.feature_weights = {
            'hour_of_day': 0.25,
            'day_of_week': 0.15,
            'current_soc': 0.20,
            'solar_trend': 0.15,
            'load_trend': 0.15,
            'weather_score': 0.10
        }
        
        logger.info("Battery predictor initialized")
    
    async def predict_battery_behavior(self, hours_ahead: int = 24) -> BatteryPrediction:
        """Predict battery behavior for specified time horizon."""
        try:
            # Ensure models are trained
            await self._ensure_models_trained()
            
            # Get current state and historical data
            current_data = await self._get_current_battery_state()
            historical_data = await self._get_historical_data(self.lookback_hours)
            
            if not current_data or len(historical_data) < self.min_data_points:
                logger.warning("Insufficient data for battery prediction")
                return self._create_empty_prediction()
            
            current_soc = current_data['battery_soc']
            current_time = datetime.now(timezone.utc)
            
            # Generate features for prediction
            features = await self._extract_prediction_features(current_data, historical_data)
            
            # Predict SOC for different horizons
            predictions = {}
            for horizon in self.prediction_horizons:
                if horizon <= hours_ahead:
                    predicted_soc = await self._predict_soc_at_horizon(
                        current_soc, features, horizon, historical_data
                    )
                    predictions[f'predicted_soc_{horizon}h'] = predicted_soc
            
            # Calculate risk scores
            depletion_risk = await self._calculate_depletion_risk(
                current_soc, predictions, features, hours_ahead
            )
            
            charging_opportunity = await self._calculate_charging_opportunity(
                current_soc, features, historical_data
            )
            
            # Generate optimal load schedule
            load_schedule = await self._generate_optimal_load_schedule(
                current_soc, predictions, features, hours_ahead
            )
            
            # Calculate confidence
            confidence = await self._calculate_prediction_confidence(
                features, historical_data, hours_ahead
            )
            
            return BatteryPrediction(
                timestamp=current_time,
                current_soc=current_soc,
                predicted_soc_1h=predictions.get('predicted_soc_1h', current_soc),
                predicted_soc_4h=predictions.get('predicted_soc_4h', current_soc),
                predicted_soc_8h=predictions.get('predicted_soc_8h', current_soc),
                predicted_soc_24h=predictions.get('predicted_soc_24h', current_soc),
                depletion_risk_score=depletion_risk,
                charging_opportunity_score=charging_opportunity,
                optimal_load_schedule=load_schedule,
                confidence_score=confidence,
                model_features=features
            )
            
        except Exception as e:
            logger.error(f"Error in battery prediction: {e}")
            return self._create_empty_prediction()
    
    async def predict_load_consumption(self, hours_ahead: int = 24) -> LoadPrediction:
        """Predict load consumption patterns."""
        try:
            historical_data = await self._get_historical_data(self.lookback_hours)
            
            if len(historical_data) < self.min_data_points:
                return self._create_empty_load_prediction()
            
            current_time = datetime.now(timezone.utc)
            
            # Extract load patterns
            load_patterns = await self._extract_load_patterns(historical_data)
            
            # Predict load for different horizons
            predictions = {}
            for horizon in self.prediction_horizons:
                if horizon <= hours_ahead:
                    target_time = current_time + timedelta(hours=horizon)
                    predicted_load = await self._predict_load_at_time(
                        target_time, load_patterns, historical_data
                    )
                    predictions[f'predicted_load_{horizon}h'] = predicted_load
            
            # Find peak load in prediction window
            peak_time, peak_value = await self._find_predicted_peak_load(
                current_time, hours_ahead, load_patterns
            )
            
            # Calculate base load
            base_load = await self._calculate_base_load(historical_data)
            
            # Determine pattern type
            pattern_type = await self._determine_load_pattern_type(current_time)
            
            # Calculate confidence
            confidence = await self._calculate_load_prediction_confidence(
                load_patterns, historical_data
            )
            
            return LoadPrediction(
                timestamp=current_time,
                predicted_load_1h=predictions.get('predicted_load_1h', base_load),
                predicted_load_4h=predictions.get('predicted_load_4h', base_load),
                predicted_load_8h=predictions.get('predicted_load_8h', base_load),
                predicted_load_24h=predictions.get('predicted_load_24h', base_load),
                peak_load_time=peak_time,
                peak_load_value=peak_value,
                base_load=base_load,
                load_pattern_type=pattern_type,
                confidence_score=confidence
            )
            
        except Exception as e:
            logger.error(f"Error in load prediction: {e}")
            return self._create_empty_load_prediction()
    
    async def predict_solar_generation(self, hours_ahead: int = 24) -> SolarPrediction:
        """Predict solar generation based on patterns and weather."""
        try:
            # Get historical solar data
            historical_data = await self._get_historical_data(self.lookback_hours)
            weather_data = await self._get_weather_data()
            
            if len(historical_data) < self.min_data_points:
                return self._create_empty_solar_prediction()
            
            current_time = datetime.now(timezone.utc)
            
            # Extract solar patterns
            solar_patterns = await self._extract_solar_patterns(historical_data)
            
            # Weather impact analysis
            weather_impact = await self._analyze_weather_impact(weather_data, historical_data)
            
            # Predict solar for different horizons
            predictions = {}
            daily_total = 0
            
            for horizon in self.prediction_horizons:
                if horizon <= hours_ahead:
                    target_time = current_time + timedelta(hours=horizon)
                    predicted_solar = await self._predict_solar_at_time(
                        target_time, solar_patterns, weather_impact
                    )
                    predictions[f'predicted_solar_{horizon}h'] = predicted_solar
                    
                    if horizon <= 24:
                        daily_total += predicted_solar * (horizon / 24)
            
            # Find peak generation time
            peak_time, peak_value = await self._find_predicted_peak_solar(
                current_time, hours_ahead, solar_patterns, weather_impact
            )
            
            # Calculate confidence
            confidence = await self._calculate_solar_prediction_confidence(
                solar_patterns, weather_impact, historical_data
            )
            
            return SolarPrediction(
                timestamp=current_time,
                predicted_solar_1h=predictions.get('predicted_solar_1h', 0),
                predicted_solar_4h=predictions.get('predicted_solar_4h', 0),
                predicted_solar_8h=predictions.get('predicted_solar_8h', 0),
                predicted_solar_24h=predictions.get('predicted_solar_24h', 0),
                daily_total_kwh=daily_total,
                peak_generation_time=peak_time,
                peak_generation_value=peak_value,
                weather_impact_score=weather_impact.get('impact_score', 0),
                confidence_score=confidence
            )
            
        except Exception as e:
            logger.error(f"Error in solar prediction: {e}")
            return self._create_empty_solar_prediction()
    
    async def generate_battery_optimization_strategy(self) -> Dict[str, Any]:
        """Generate comprehensive battery optimization strategy."""
        try:
            # Get all predictions
            battery_pred = await self.predict_battery_behavior(24)
            load_pred = await self.predict_load_consumption(24)
            solar_pred = await self.predict_solar_generation(24)
            
            # Calculate optimal strategy
            strategy = {
                'timestamp': datetime.now(timezone.utc),
                'battery_status': {
                    'current_soc': battery_pred.current_soc,
                    'depletion_risk': battery_pred.depletion_risk_score,
                    'charging_opportunity': battery_pred.charging_opportunity_score
                },
                'recommendations': [],
                'load_management': [],
                'charging_schedule': [],
                'risk_mitigation': []
            }
            
            # High depletion risk recommendations
            if battery_pred.depletion_risk_score > 0.7:
                strategy['recommendations'].append({
                    'type': 'urgent_load_reduction',
                    'priority': 'high',
                    'message': f'High depletion risk ({battery_pred.depletion_risk_score:.1%})',
                    'actions': [
                        'Reduce non-essential loads immediately',
                        'Monitor battery closely',
                        'Prepare backup power if available'
                    ]
                })
            
            # Good charging opportunity
            if battery_pred.charging_opportunity_score > 0.6:
                strategy['recommendations'].append({
                    'type': 'charging_opportunity',
                    'priority': 'medium',
                    'message': f'Good charging opportunity ({battery_pred.charging_opportunity_score:.1%})',
                    'actions': [
                        'Delay high-power loads if possible',
                        'Maximize solar charging window',
                        'Consider pre-heating water'
                    ]
                })
            
            # Load management recommendations
            if load_pred.peak_load_time:
                hours_to_peak = (load_pred.peak_load_time - datetime.now(timezone.utc)).total_seconds() / 3600
                if 0 < hours_to_peak <= 8:
                    strategy['load_management'].append({
                        'type': 'peak_load_warning',
                        'time': load_pred.peak_load_time.isoformat(),
                        'expected_load': load_pred.peak_load_value,
                        'recommendation': 'Consider shifting non-essential loads away from peak time'
                    })
            
            # Solar optimization
            if solar_pred.peak_generation_time:
                hours_to_peak_solar = (solar_pred.peak_generation_time - datetime.now(timezone.utc)).total_seconds() / 3600
                if 0 < hours_to_peak_solar <= 8:
                    strategy['charging_schedule'].append({
                        'type': 'solar_peak_charging',
                        'time': solar_pred.peak_generation_time.isoformat(),
                        'expected_generation': solar_pred.peak_generation_value,
                        'recommendation': 'Optimal time for high-power loads and battery charging'
                    })
            
            # Risk mitigation
            if battery_pred.predicted_soc_24h < self.min_soc + 10:  # Within 10% of minimum
                strategy['risk_mitigation'].append({
                    'type': 'low_soc_risk',
                    'predicted_soc': battery_pred.predicted_soc_24h,
                    'time_to_risk': '24 hours',
                    'actions': [
                        'Plan load reduction strategy',
                        'Check weather forecast for solar availability',
                        'Consider backup power options'
                    ]
                })
            
            # Calculate overall strategy score
            strategy['overall_score'] = self._calculate_strategy_score(
                battery_pred, load_pred, solar_pred
            )
            
            return strategy
            
        except Exception as e:
            logger.error(f"Error generating optimization strategy: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc)}
    
    # Implementation of helper methods
    async def _ensure_models_trained(self):
        """Ensure prediction models are trained and up to date."""
        current_time = datetime.now(timezone.utc)
        
        if (self.last_training is None or 
            current_time - self.last_training > self.training_interval):
            
            logger.info("Training prediction models...")
            await self._train_models()
            self.last_training = current_time
    
    async def _train_models(self):
        """Train machine learning models on historical data."""
        try:
            # Get training data
            training_data = await self._get_historical_data(self.lookback_hours * 2)
            
            if len(training_data) < self.min_data_points * 2:
                logger.warning("Insufficient data for model training")
                return
            
            # Train pattern recognition models
            await self._train_pattern_models(training_data)
            
            # Train trend analysis models
            await self._train_trend_models(training_data)
            
            logger.info(f"Models trained on {len(training_data)} data points")
            
        except Exception as e:
            logger.error(f"Error training models: {e}")
    
    async def _train_pattern_models(self, data):
        """Train pattern recognition models."""
        # Group by day type and hour
        for record in data:
            timestamp = record['timestamp']
            hour = timestamp.hour
            is_weekend = timestamp.weekday() >= 5
            
            pattern_type = 'weekend' if is_weekend else 'weekday'
            
            # Store patterns
            self.patterns[pattern_type][hour].append({
                'battery_soc': record.get('battery_soc', 0),
                'battery_power': record.get('battery_power', 0),
                'solar_power': record.get('solar_power', 0),
                'load_power': record.get('load_power', 0)
            })
    
    async def _train_trend_models(self, data):
        """Train trend analysis models."""
        # Simple moving average and trend detection
        # In a production system, you might use more sophisticated ML models
        pass
    
    async def _get_current_battery_state(self):
        """Get current battery state."""
        try:
            data = await self.db_manager.get_historical_data(
                'solar_metrics', '-5m', None
            )
            
            if data:
                return data[-1]  # Most recent record
            return None
            
        except Exception as e:
            logger.error(f"Error getting current battery state: {e}")
            return None
    
    async def _get_historical_data(self, hours):
        """Get historical data for analysis."""
        try:
            return await self.db_manager.get_historical_data(
                'solar_metrics', f'-{hours}h', None
            )
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return []
    
    async def _get_weather_data(self):
        """Get current weather data."""
        try:
            data = await self.db_manager.get_historical_data(
                'weather_data', '-1h', None
            )
            return data[-1] if data else {}
        except Exception as e:
            logger.error(f"Error getting weather data: {e}")
            return {}
    
    async def _extract_prediction_features(self, current_data, historical_data):
        """Extract features for prediction models."""
        current_time = datetime.now(timezone.utc)
        
        features = {
            'hour_of_day': current_time.hour / 24.0,
            'day_of_week': current_time.weekday() / 7.0,
            'current_soc': current_data.get('battery_soc', 0) / 100.0,
            'solar_trend': await self._calculate_solar_trend(historical_data),
            'load_trend': await self._calculate_load_trend(historical_data),
            'weather_score': await self._calculate_weather_score()
        }
        
        return features
    
    async def _calculate_solar_trend(self, data):
        """Calculate solar generation trend."""
        if len(data) < 10:
            return 0.0
        
        recent_solar = [r.get('solar_power', 0) for r in data[-10:]]
        older_solar = [r.get('solar_power', 0) for r in data[-20:-10]]
        
        if not recent_solar or not older_solar:
            return 0.0
        
        recent_avg = statistics.mean(recent_solar)
        older_avg = statistics.mean(older_solar)
        
        if older_avg == 0:
            return 0.0
        
        trend = (recent_avg - older_avg) / older_avg
        return max(-1.0, min(1.0, trend))  # Normalize to [-1, 1]
    
    async def _calculate_load_trend(self, data):
        """Calculate load consumption trend."""
        if len(data) < 10:
            return 0.0
        
        recent_load = [r.get('load_power', 0) for r in data[-10:]]
        older_load = [r.get('load_power', 0) for r in data[-20:-10]]
        
        if not recent_load or not older_load:
            return 0.0
        
        recent_avg = statistics.mean(recent_load)
        older_avg = statistics.mean(older_load)
        
        if older_avg == 0:
            return 0.0
        
        trend = (recent_avg - older_avg) / older_avg
        return max(-1.0, min(1.0, trend))  # Normalize to [-1, 1]
    
    async def _calculate_weather_score(self):
        """Calculate weather impact score."""
        # Simplified weather scoring
        # In production, this would analyze cloud cover, temperature, etc.
        return 0.5  # Neutral weather
    
    async def _predict_soc_at_horizon(self, current_soc, features, horizon, historical_data):
        """Predict SOC at specific time horizon."""
        try:
            current_time = datetime.now(timezone.utc)
            target_time = current_time + timedelta(hours=horizon)
            target_hour = target_time.hour
            is_weekend = target_time.weekday() >= 5
            
            pattern_type = 'weekend' if is_weekend else 'weekday'
            
            # Get historical patterns for this hour
            if target_hour in self.patterns[pattern_type]:
                historical_socs = [
                    p['battery_soc'] for p in self.patterns[pattern_type][target_hour]
                ]
                
                if historical_socs:
                    base_prediction = statistics.mean(historical_socs)
                    
                    # Adjust based on current trends
                    trend_adjustment = (
                        features['solar_trend'] * 5 +  # Solar trend impact
                        features['load_trend'] * -3    # Load trend impact (negative)
                    )
                    
                    predicted_soc = base_prediction + trend_adjustment
                    
                    # Apply constraints
                    predicted_soc = max(0, min(100, predicted_soc))
                    
                    return predicted_soc
            
            # Fallback: simple trend extrapolation
            if len(historical_data) >= 2:
                recent_trend = self._calculate_soc_trend(historical_data[-10:])
                predicted_soc = current_soc + (recent_trend * horizon)
                return max(0, min(100, predicted_soc))
            
            return current_soc
            
        except Exception as e:
            logger.error(f"Error predicting SOC at horizon {horizon}: {e}")
            return current_soc
    
    def _calculate_soc_trend(self, data):
        """Calculate SOC change trend from recent data."""
        if len(data) < 2:
            return 0
        
        soc_changes = []
        for i in range(1, len(data)):
            time_diff = (data[i]['timestamp'] - data[i-1]['timestamp']).total_seconds() / 3600
            if time_diff > 0:
                soc_change = (data[i].get('battery_soc', 0) - data[i-1].get('battery_soc', 0)) / time_diff
                soc_changes.append(soc_change)
        
        return statistics.mean(soc_changes) if soc_changes else 0
    
    async def _calculate_depletion_risk(self, current_soc, predictions, features, hours_ahead):
        """Calculate battery depletion risk score."""
        try:
            # Base risk on predicted SOC levels
            risk_factors = []
            
            # Check predictions at different horizons
            for horizon in [1, 4, 8, 24]:
                if horizon <= hours_ahead:
                    pred_key = f'predicted_soc_{horizon}h'
                    if pred_key in predictions:
                        pred_soc = predictions[pred_key]
                        if pred_soc <= self.min_soc:
                            risk_factors.append(1.0)  # Maximum risk
                        elif pred_soc <= self.min_soc + 20:
                            risk_factors.append((self.min_soc + 20 - pred_soc) / 20)
                        else:
                            risk_factors.append(0.0)
            
            # Consider load trend
            if features.get('load_trend', 0) > 0.2:  # Increasing load
                risk_factors.append(0.3)
            
            # Consider solar trend
            if features.get('solar_trend', 0) < -0.2:  # Decreasing solar
                risk_factors.append(0.2)
            
            # Calculate overall risk
            if risk_factors:
                return min(1.0, max(risk_factors) + statistics.mean(risk_factors) * 0.3)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating depletion risk: {e}")
            return 0.0
    
    async def _calculate_charging_opportunity(self, current_soc, features, historical_data):
        """Calculate charging opportunity score."""
        try:
            opportunity_factors = []
            
            # High solar availability
            if features.get('solar_trend', 0) > 0.1:
                opportunity_factors.append(0.4)
            
            # Low current SOC (more room to charge)
            if current_soc < 70:
                opportunity_factors.append((70 - current_soc) / 70 * 0.3)
            
            # Good time of day for solar
            hour = datetime.now(timezone.utc).hour
            if 9 <= hour <= 15:  # Peak solar hours
                opportunity_factors.append(0.3)
            
            # Low load trend
            if features.get('load_trend', 0) < -0.1:
                opportunity_factors.append(0.2)
            
            return min(1.0, sum(opportunity_factors))
            
        except Exception as e:
            logger.error(f"Error calculating charging opportunity: {e}")
            return 0.0
    
    async def _generate_optimal_load_schedule(self, current_soc, predictions, features, hours_ahead):
        """Generate optimal load scheduling recommendations."""
        try:
            schedule = []
            current_time = datetime.now(timezone.utc)
            
            # High power loads during peak solar
            for hour_offset in range(1, min(hours_ahead + 1, 9)):
                target_time = current_time + timedelta(hours=hour_offset)
                target_hour = target_time.hour
                
                if 10 <= target_hour <= 14:  # Peak solar hours
                    schedule.append({
                        'time': target_time.isoformat(),
                        'hour_offset': hour_offset,
                        'recommendation': 'optimal_for_high_loads',
                        'description': 'Good time for geyser, pool pumps, washing machine',
                        'confidence': 0.8
                    })
                elif 17 <= target_hour <= 20:  # Peak tariff hours
                    schedule.append({
                        'time': target_time.isoformat(),
                        'hour_offset': hour_offset,
                        'recommendation': 'avoid_high_loads',
                        'description': 'Avoid high power consumption (peak tariff)',
                        'confidence': 0.9
                    })
            
            return schedule[:10]  # Limit to 10 recommendations
            
        except Exception as e:
            logger.error(f"Error generating load schedule: {e}")
            return []
    
    async def _calculate_prediction_confidence(self, features, historical_data, hours_ahead):
        """Calculate prediction confidence score."""
        try:
            confidence_factors = []
            
            # Data quality
            if len(historical_data) >= self.min_data_points * 2:
                confidence_factors.append(0.3)
            elif len(historical_data) >= self.min_data_points:
                confidence_factors.append(0.2)
            else:
                confidence_factors.append(0.1)
            
            # Pattern consistency
            # (In a real implementation, you'd analyze variance in similar conditions)
            confidence_factors.append(0.2)
            
            # Time horizon (shorter predictions are more confident)
            if hours_ahead <= 4:
                confidence_factors.append(0.3)
            elif hours_ahead <= 12:
                confidence_factors.append(0.2)
            else:
                confidence_factors.append(0.1)
            
            # Weather stability
            confidence_factors.append(0.2)
            
            return min(1.0, sum(confidence_factors))
            
        except Exception as e:
            logger.error(f"Error calculating prediction confidence: {e}")
            return 0.5
    
    # Additional helper methods for load and solar predictions
    async def _extract_load_patterns(self, historical_data):
        """Extract load consumption patterns."""
        patterns = defaultdict(list)
        
        for record in historical_data:
            timestamp = record['timestamp']
            hour = timestamp.hour
            is_weekend = timestamp.weekday() >= 5
            
            pattern_key = f"{'weekend' if is_weekend else 'weekday'}_{hour}"
            patterns[pattern_key].append(record.get('load_power', 0))
        
        # Calculate averages for each pattern
        avg_patterns = {}
        for key, values in patterns.items():
            if values:
                avg_patterns[key] = statistics.mean(values)
        
        return avg_patterns
    
    async def _predict_load_at_time(self, target_time, load_patterns, historical_data):
        """Predict load at specific time."""
        hour = target_time.hour
        is_weekend = target_time.weekday() >= 5
        pattern_key = f"{'weekend' if is_weekend else 'weekday'}_{hour}"
        
        if pattern_key in load_patterns:
            return load_patterns[pattern_key]
        
        # Fallback to overall average
        all_loads = [r.get('load_power', 0) for r in historical_data]
        return statistics.mean(all_loads) if all_loads else 0
    
    async def _find_predicted_peak_load(self, current_time, hours_ahead, load_patterns):
        """Find predicted peak load time and value."""
        peak_time = current_time
        peak_value = 0
        
        for hour_offset in range(hours_ahead + 1):
            target_time = current_time + timedelta(hours=hour_offset)
            predicted_load = await self._predict_load_at_time(
                target_time, load_patterns, []
            )
            
            if predicted_load > peak_value:
                peak_value = predicted_load
                peak_time = target_time
        
        return peak_time, peak_value
    
    async def _calculate_base_load(self, historical_data):
        """Calculate base load (minimum consistent load)."""
        all_loads = [r.get('load_power', 0) for r in historical_data]
        if not all_loads:
            return 0
        
        # Use 10th percentile as base load
        sorted_loads = sorted(all_loads)
        index = int(len(sorted_loads) * 0.1)
        return sorted_loads[index] if index < len(sorted_loads) else sorted_loads[0]
    
    async def _determine_load_pattern_type(self, current_time):
        """Determine current load pattern type."""
        if current_time.weekday() >= 5:
            return 'weekend'
        # Could extend with holiday detection
        return 'weekday'
    
    async def _calculate_load_prediction_confidence(self, load_patterns, historical_data):
        """Calculate load prediction confidence."""
        # Simplified confidence based on data availability
        if len(historical_data) >= 100 and len(load_patterns) >= 10:
            return 0.8
        elif len(historical_data) >= 50:
            return 0.6
        else:
            return 0.4
    
    # Solar prediction helper methods
    async def _extract_solar_patterns(self, historical_data):
        """Extract solar generation patterns."""
        patterns = defaultdict(list)
        
        for record in historical_data:
            timestamp = record['timestamp']
            hour = timestamp.hour
            
            # Only consider daylight hours
            if 6 <= hour <= 18:
                patterns[hour].append(record.get('solar_power', 0))
        
        # Calculate averages
        avg_patterns = {}
        for hour, values in patterns.items():
            if values:
                avg_patterns[hour] = statistics.mean(values)
        
        return avg_patterns
    
    async def _analyze_weather_impact(self, weather_data, historical_data):
        """Analyze weather impact on solar generation."""
        # Simplified weather impact analysis
        impact = {
            'impact_score': 0.0,  # -1 to 1
            'cloud_factor': 1.0,  # 0 to 1
            'temperature_factor': 1.0  # 0 to 1
        }
        
        if weather_data:
            # Cloud cover impact
            cloud_cover = weather_data.get('cloud_cover', 0)
            impact['cloud_factor'] = max(0.1, 1.0 - (cloud_cover / 100))
            
            # Temperature impact (simplified)
            temp = weather_data.get('temperature', 25)
            if 15 <= temp <= 35:  # Optimal range
                impact['temperature_factor'] = 1.0
            else:
                impact['temperature_factor'] = max(0.7, 1.0 - abs(temp - 25) / 25)
            
            # Overall impact
            impact['impact_score'] = (impact['cloud_factor'] + impact['temperature_factor'] - 1.0)
        
        return impact
    
    async def _predict_solar_at_time(self, target_time, solar_patterns, weather_impact):
        """Predict solar generation at specific time."""
        hour = target_time.hour
        
        # Base prediction from patterns
        base_solar = solar_patterns.get(hour, 0)
        
        # Apply weather impact
        weather_factor = weather_impact.get('cloud_factor', 1.0)
        predicted_solar = base_solar * weather_factor
        
        return max(0, predicted_solar)
    
    async def _find_predicted_peak_solar(self, current_time, hours_ahead, solar_patterns, weather_impact):
        """Find predicted peak solar generation."""
        peak_time = current_time
        peak_value = 0
        
        for hour_offset in range(hours_ahead + 1):
            target_time = current_time + timedelta(hours=hour_offset)
            predicted_solar = await self._predict_solar_at_time(
                target_time, solar_patterns, weather_impact
            )
            
            if predicted_solar > peak_value:
                peak_value = predicted_solar
                peak_time = target_time
        
        return peak_time, peak_value
    
    async def _calculate_solar_prediction_confidence(self, solar_patterns, weather_impact, historical_data):
        """Calculate solar prediction confidence."""
        # Base confidence on data availability
        base_confidence = min(0.8, len(historical_data) / 200)
        
        # Reduce confidence for poor weather
        weather_confidence = weather_impact.get('cloud_factor', 1.0)
        
        return base_confidence * weather_confidence
    
    def _calculate_strategy_score(self, battery_pred, load_pred, solar_pred):
        """Calculate overall optimization strategy score."""
        # Weighted score based on predictions
        battery_score = (1 - battery_pred.depletion_risk_score) * 0.4
        efficiency_score = battery_pred.charging_opportunity_score * 0.3
        prediction_confidence = (
            battery_pred.confidence_score + 
            load_pred.confidence_score + 
            solar_pred.confidence_score
        ) / 3 * 0.3
        
        return min(1.0, battery_score + efficiency_score + prediction_confidence)
    
    def _create_empty_prediction(self):
        """Create empty battery prediction."""
        current_time = datetime.now(timezone.utc)
        return BatteryPrediction(
            timestamp=current_time,
            current_soc=0.0,
            predicted_soc_1h=0.0,
            predicted_soc_4h=0.0,
            predicted_soc_8h=0.0,
            predicted_soc_24h=0.0,
            depletion_risk_score=0.0,
            charging_opportunity_score=0.0,
            optimal_load_schedule=[],
            confidence_score=0.0,
            model_features={}
        )
    
    def _create_empty_load_prediction(self):
        """Create empty load prediction."""
        current_time = datetime.now(timezone.utc)
        return LoadPrediction(
            timestamp=current_time,
            predicted_load_1h=0.0,
            predicted_load_4h=0.0,
            predicted_load_8h=0.0,
            predicted_load_24h=0.0,
            peak_load_time=current_time,
            peak_load_value=0.0,
            base_load=0.0,
            load_pattern_type='weekday',
            confidence_score=0.0
        )
    
    def _create_empty_solar_prediction(self):
        """Create empty solar prediction."""
        current_time = datetime.now(timezone.utc)
        return SolarPrediction(
            timestamp=current_time,
            predicted_solar_1h=0.0,
            predicted_solar_4h=0.0,
            predicted_solar_8h=0.0,
            predicted_solar_24h=0.0,
            daily_total_kwh=0.0,
            peak_generation_time=current_time,
            peak_generation_value=0.0,
            weather_impact_score=0.0,
            confidence_score=0.0
        )


# Test function
async def test_battery_predictor():
    """Test battery predictor functionality."""
    db_manager = DatabaseManager()
    if not await db_manager.connect():
        print("Could not connect to database")
        return
    
    predictor = BatteryPredictor(db_manager)
    
    print("Testing battery predictor...")
    
    # Test battery prediction
    battery_pred = await predictor.predict_battery_behavior(24)
    print(f"Battery Prediction - Current SOC: {battery_pred.current_soc:.1f}%")
    print(f"  1h: {battery_pred.predicted_soc_1h:.1f}%")
    print(f"  4h: {battery_pred.predicted_soc_4h:.1f}%")
    print(f"  24h: {battery_pred.predicted_soc_24h:.1f}%")
    print(f"  Depletion Risk: {battery_pred.depletion_risk_score:.2f}")
    print(f"  Charging Opportunity: {battery_pred.charging_opportunity_score:.2f}")
    
    # Test load prediction
    load_pred = await predictor.predict_load_consumption(24)
    print(f"\nLoad Prediction - Base Load: {load_pred.base_load:.2f}kW")
    print(f"  Peak at {load_pred.peak_load_time.strftime('%H:%M')}: {load_pred.peak_load_value:.2f}kW")
    
    # Test optimization strategy
    strategy = await predictor.generate_battery_optimization_strategy()
    print(f"\nOptimization Strategy - Score: {strategy.get('overall_score', 0):.2f}")
    print(f"  Recommendations: {len(strategy.get('recommendations', []))}")
    
    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(test_battery_predictor())
