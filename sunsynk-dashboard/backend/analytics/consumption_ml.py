"""
Consumption Pattern Recognition - Phase 6 Task 066
Machine learning models for consumption pattern recognition and optimization
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
from collections import defaultdict
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class ConsumptionPattern:
    """Detected consumption pattern"""
    pattern_type: str  # 'daily', 'weekly', 'seasonal'
    peak_hours: List[int]
    average_consumption: float
    peak_consumption: float
    efficiency_score: float
    pattern_confidence: float
    
@dataclass
class ConsumptionAnomaly:
    """Detected consumption anomaly"""
    timestamp: datetime
    expected_consumption: float
    actual_consumption: float
    deviation_percentage: float
    anomaly_type: str  # 'spike', 'low', 'unusual_pattern'
    severity: str  # 'low', 'medium', 'high'

@dataclass
class OptimizationRecommendation:
    """Energy optimization recommendation"""
    category: str  # 'load_shifting', 'efficiency', 'solar_usage'
    title: str
    description: str
    potential_savings: float  # kWh per day
    confidence: float
    priority: str  # 'high', 'medium', 'low'

class ConsumptionMLAnalyzer:
    """
    Machine Learning Consumption Pattern Analyzer
    Uses statistical analysis and pattern recognition for energy optimization
    """
    
    def __init__(self):
        self.patterns_cache = {}
        self.baseline_consumption = {}
        self.learning_period_days = 30
        
    def analyze_consumption_patterns(self, historical_data: List[Dict]) -> List[ConsumptionPattern]:
        """
        Analyze consumption patterns using ML techniques
        """
        if not historical_data or len(historical_data) < 24:
            logger.warning("Insufficient data for pattern analysis")
            return []
        
        try:
            df = pd.DataFrame(historical_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
            
            patterns = []
            
            # Daily pattern analysis
            daily_pattern = self._analyze_daily_pattern(df)
            if daily_pattern:
                patterns.append(daily_pattern)
            
            # Weekly pattern analysis
            weekly_pattern = self._analyze_weekly_pattern(df)
            if weekly_pattern:
                patterns.append(weekly_pattern)
            
            # Seasonal pattern analysis (if enough data)
            if len(df) > 24 * 7:  # More than a week of data
                seasonal_pattern = self._analyze_seasonal_pattern(df)
                if seasonal_pattern:
                    patterns.append(seasonal_pattern)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Consumption pattern analysis error: {e}")
            return []
    
    def _analyze_daily_pattern(self, df: pd.DataFrame) -> Optional[ConsumptionPattern]:
        """Analyze daily consumption patterns"""
        try:
            # Group by hour of day
            hourly_consumption = df.groupby(df.index.hour)['consumption'].agg(['mean', 'std']).fillna(0)
            
            # Find peak hours (top 25% of consumption)
            peak_threshold = hourly_consumption['mean'].quantile(0.75)
            peak_hours = hourly_consumption[hourly_consumption['mean'] >= peak_threshold].index.tolist()
            
            # Calculate metrics
            avg_consumption = hourly_consumption['mean'].mean()
            peak_consumption = hourly_consumption['mean'].max()
            
            # Calculate efficiency score (lower variation = higher efficiency)
            variation_coefficient = hourly_consumption['mean'].std() / avg_consumption if avg_consumption > 0 else 1
            efficiency_score = max(0, 1 - variation_coefficient)
            
            # Pattern confidence based on data consistency
            pattern_confidence = 1 - (hourly_consumption['std'].mean() / peak_consumption) if peak_consumption > 0 else 0
            pattern_confidence = max(0, min(1, pattern_confidence))
            
            return ConsumptionPattern(
                pattern_type='daily',
                peak_hours=peak_hours,
                average_consumption=round(avg_consumption, 3),
                peak_consumption=round(peak_consumption, 3),
                efficiency_score=round(efficiency_score, 3),
                pattern_confidence=round(pattern_confidence, 3)
            )
            
        except Exception as e:
            logger.error(f"Daily pattern analysis error: {e}")
            return None
    
    def _analyze_weekly_pattern(self, df: pd.DataFrame) -> Optional[ConsumptionPattern]:
        """Analyze weekly consumption patterns"""
        try:
            if len(df) < 24 * 7:  # Less than a week
                return None
                
            # Group by day of week
            df['weekday'] = df.index.weekday
            weekly_consumption = df.groupby('weekday')['consumption'].agg(['mean', 'std']).fillna(0)
            
            # Find peak days (weekday 0=Monday, 6=Sunday)
            peak_threshold = weekly_consumption['mean'].quantile(0.75)
            peak_days = weekly_consumption[weekly_consumption['mean'] >= peak_threshold].index.tolist()
            
            avg_consumption = weekly_consumption['mean'].mean()
            peak_consumption = weekly_consumption['mean'].max()
            
            # Weekly efficiency (weekend vs weekday consistency)
            weekday_avg = weekly_consumption.loc[0:4, 'mean'].mean()  # Mon-Fri
            weekend_avg = weekly_consumption.loc[5:6, 'mean'].mean()  # Sat-Sun
            
            if weekday_avg > 0:
                weekly_variation = abs(weekend_avg - weekday_avg) / weekday_avg
                efficiency_score = max(0, 1 - weekly_variation)
            else:
                efficiency_score = 0
            
            pattern_confidence = 1 - (weekly_consumption['std'].mean() / peak_consumption) if peak_consumption > 0 else 0
            pattern_confidence = max(0, min(1, pattern_confidence))
            
            return ConsumptionPattern(
                pattern_type='weekly',
                peak_hours=peak_days,  # Actually peak days for weekly pattern
                average_consumption=round(avg_consumption, 3),
                peak_consumption=round(peak_consumption, 3),
                efficiency_score=round(efficiency_score, 3),
                pattern_confidence=round(pattern_confidence, 3)
            )
            
        except Exception as e:
            logger.error(f"Weekly pattern analysis error: {e}")
            return None
    
    def _analyze_seasonal_pattern(self, df: pd.DataFrame) -> Optional[ConsumptionPattern]:
        """Analyze seasonal consumption patterns"""
        try:
            # Simple seasonal analysis based on month/week
            df['month'] = df.index.month
            monthly_consumption = df.groupby('month')['consumption'].agg(['mean', 'std']).fillna(0)
            
            if len(monthly_consumption) < 2:
                return None
            
            # Find peak months
            peak_threshold = monthly_consumption['mean'].quantile(0.75)
            peak_months = monthly_consumption[monthly_consumption['mean'] >= peak_threshold].index.tolist()
            
            avg_consumption = monthly_consumption['mean'].mean()
            peak_consumption = monthly_consumption['mean'].max()
            
            # Seasonal efficiency (consistency across months)
            seasonal_variation = monthly_consumption['mean'].std() / avg_consumption if avg_consumption > 0 else 1
            efficiency_score = max(0, 1 - seasonal_variation)
            
            pattern_confidence = 0.7  # Lower confidence for seasonal patterns with limited data
            
            return ConsumptionPattern(
                pattern_type='seasonal',
                peak_hours=peak_months,  # Actually peak months for seasonal pattern
                average_consumption=round(avg_consumption, 3),
                peak_consumption=round(peak_consumption, 3),
                efficiency_score=round(efficiency_score, 3),
                pattern_confidence=round(pattern_confidence, 3)
            )
            
        except Exception as e:
            logger.error(f"Seasonal pattern analysis error: {e}")
            return None
    
    def detect_anomalies(self, historical_data: List[Dict], window_hours: int = 24) -> List[ConsumptionAnomaly]:
        """
        Detect consumption anomalies using statistical analysis
        """
        if not historical_data or len(historical_data) < window_hours * 2:
            return []
        
        try:
            df = pd.DataFrame(historical_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp').sort_index()
            
            anomalies = []
            consumption = df['consumption'].fillna(0)
            
            # Calculate rolling statistics
            rolling_mean = consumption.rolling(window=window_hours, center=True).mean()
            rolling_std = consumption.rolling(window=window_hours, center=True).std()
            
            # Define anomaly thresholds (2 standard deviations)
            upper_threshold = rolling_mean + (2 * rolling_std)
            lower_threshold = rolling_mean - (2 * rolling_std)
            
            # Detect anomalies
            for idx, row in df.iterrows():
                current_consumption = row['consumption']
                expected_consumption = rolling_mean.loc[idx] if idx in rolling_mean.index else current_consumption
                
                if pd.isna(expected_consumption):
                    continue
                
                # Check for anomalies
                is_high_anomaly = current_consumption > upper_threshold.loc[idx] if idx in upper_threshold.index else False
                is_low_anomaly = current_consumption < lower_threshold.loc[idx] if idx in lower_threshold.index else False
                
                if is_high_anomaly or is_low_anomaly:
                    deviation = abs(current_consumption - expected_consumption)
                    deviation_percentage = (deviation / expected_consumption * 100) if expected_consumption > 0 else 0
                    
                    # Determine anomaly type and severity
                    if is_high_anomaly:
                        anomaly_type = 'spike'
                        severity = 'high' if deviation_percentage > 100 else 'medium' if deviation_percentage > 50 else 'low'
                    else:
                        anomaly_type = 'low'
                        severity = 'medium' if deviation_percentage > 50 else 'low'
                    
                    anomaly = ConsumptionAnomaly(
                        timestamp=idx,
                        expected_consumption=round(expected_consumption, 3),
                        actual_consumption=round(current_consumption, 3),
                        deviation_percentage=round(deviation_percentage, 1),
                        anomaly_type=anomaly_type,
                        severity=severity
                    )
                    anomalies.append(anomaly)
            
            # Sort by severity and timestamp
            anomalies.sort(key=lambda x: (x.severity, x.timestamp), reverse=True)
            
            return anomalies[:10]  # Return top 10 anomalies
            
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return []
    
    def generate_optimization_recommendations(self, 
                                            patterns: List[ConsumptionPattern],
                                            solar_data: List[Dict],
                                            anomalies: List[ConsumptionAnomaly]) -> List[OptimizationRecommendation]:
        """
        Generate energy optimization recommendations based on ML analysis
        """
        recommendations = []
        
        try:
            # Load shifting recommendations
            for pattern in patterns:
                if pattern.pattern_type == 'daily' and pattern.peak_hours:
                    # Recommend shifting load away from peak hours
                    peak_hours_str = ', '.join([f"{h}:00" for h in pattern.peak_hours])
                    
                    recommendation = OptimizationRecommendation(
                        category='load_shifting',
                        title='Optimize Peak Hour Usage',
                        description=f"High consumption detected during {peak_hours_str}. Consider shifting non-essential loads to off-peak hours (2AM-6AM) to reduce costs.",
                        potential_savings=pattern.peak_consumption * 0.3,  # Estimated 30% savings
                        confidence=pattern.pattern_confidence,
                        priority='high' if pattern.pattern_confidence > 0.7 else 'medium'
                    )
                    recommendations.append(recommendation)
            
            # Solar usage optimization
            if solar_data:
                df_solar = pd.DataFrame(solar_data)
                avg_solar = df_solar['solar_power'].mean() if 'solar_power' in df_solar.columns else 0
                
                if avg_solar > 0:
                    recommendation = OptimizationRecommendation(
                        category='solar_usage',
                        title='Maximize Solar Energy Usage',
                        description=f"Average solar production: {avg_solar:.2f}kW. Schedule high-consumption appliances (washing machine, geyser) during peak solar hours (10AM-2PM).",
                        potential_savings=avg_solar * 0.4,  # 40% of solar production
                        confidence=0.8,
                        priority='high'
                    )
                    recommendations.append(recommendation)
            
            # Anomaly-based recommendations
            high_severity_anomalies = [a for a in anomalies if a.severity == 'high']
            if high_severity_anomalies:
                spike_anomalies = [a for a in high_severity_anomalies if a.anomaly_type == 'spike']
                if spike_anomalies:
                    avg_spike = np.mean([a.actual_consumption for a in spike_anomalies])
                    
                    recommendation = OptimizationRecommendation(
                        category='efficiency',
                        title='Investigate High Consumption Spikes',
                        description=f"Detected {len(spike_anomalies)} high consumption spikes averaging {avg_spike:.2f}kW. Check for faulty appliances or inefficient devices.",
                        potential_savings=avg_spike * 0.5 * len(spike_anomalies) / 30,  # Daily savings estimate
                        confidence=0.7,
                        priority='high'
                    )
                    recommendations.append(recommendation)
            
            # General efficiency recommendations
            overall_efficiency = np.mean([p.efficiency_score for p in patterns]) if patterns else 0
            if overall_efficiency < 0.6:
                recommendation = OptimizationRecommendation(
                    category='efficiency',
                    title='Improve Energy Efficiency',
                    description=f"Energy efficiency score: {overall_efficiency:.1%}. Consider upgrading to energy-efficient appliances and improving home insulation.",
                    potential_savings=2.0,  # Estimated 2kWh daily savings
                    confidence=0.6,
                    priority='medium'
                )
                recommendations.append(recommendation)
            
            # Sort by priority and confidence
            priority_order = {'high': 3, 'medium': 2, 'low': 1}
            recommendations.sort(key=lambda x: (priority_order[x.priority], x.confidence), reverse=True)
            
            return recommendations[:5]  # Return top 5 recommendations
            
        except Exception as e:
            logger.error(f"Optimization recommendations error: {e}")
            return []
    
    def predict_consumption(self, historical_data: List[Dict], hours_ahead: int = 24) -> List[Dict]:
        """
        Predict future consumption based on learned patterns
        """
        if not historical_data or len(historical_data) < 24:
            return []
        
        try:
            df = pd.DataFrame(historical_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp').sort_index()
            
            # Use simple pattern-based prediction
            predictions = []
            last_timestamp = df.index[-1]
            
            # Calculate hourly averages for pattern
            hourly_pattern = df.groupby(df.index.hour)['consumption'].mean()
            daily_avg = df['consumption'].mean()
            
            for i in range(hours_ahead):
                future_timestamp = last_timestamp + timedelta(hours=i+1)
                future_hour = future_timestamp.hour
                
                # Base prediction on hourly pattern
                if future_hour in hourly_pattern.index:
                    base_prediction = hourly_pattern[future_hour]
                else:
                    base_prediction = daily_avg
                
                # Add some trend adjustment (simplified)
                recent_trend = df['consumption'].tail(12).mean() / daily_avg if daily_avg > 0 else 1
                predicted_consumption = base_prediction * recent_trend
                
                # Add confidence based on pattern strength
                pattern_strength = 1 - (hourly_pattern.std() / hourly_pattern.mean()) if hourly_pattern.mean() > 0 else 0
                confidence = max(0.3, min(0.9, pattern_strength))
                
                predictions.append({
                    'timestamp': future_timestamp,
                    'predicted_consumption': round(max(0, predicted_consumption), 3),
                    'confidence': round(confidence, 2),
                    'model_type': 'pattern_based'
                })
            
            return predictions
            
        except Exception as e:
            logger.error(f"Consumption prediction error: {e}")
            return []

# Global instance
consumption_analyzer = ConsumptionMLAnalyzer()
