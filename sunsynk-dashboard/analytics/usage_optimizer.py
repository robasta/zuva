"""
Usage Optimization Engine for Sunsynk Solar Dashboard.
Provides intelligent load management and energy optimization recommendations.
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
from collections import defaultdict

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from collector.database import DatabaseManager
from analytics.battery_predictor import BatteryPredictor
from analytics.weather_analyzer import WeatherAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class OptimizationRecommendation:
    """Optimization recommendation."""
    id: str
    type: str  # load_shift, battery_management, solar_utilization
    priority: str  # low, medium, high, critical
    title: str
    description: str
    potential_savings: float  # kWh or cost savings
    confidence: float  # 0-1
    time_window: Tuple[datetime, datetime]
    actions: List[str]
    impact_score: float  # 0-100


@dataclass
class DeviceSchedule:
    """Alias for LoadSchedule for backward compatibility."""
    timestamp: datetime
    device_type: str
    optimal_start_time: datetime
    duration_hours: float
    power_rating: float
    reason: str
    savings_potential: float
    confidence: float


@dataclass
class LoadSchedule:
    """Optimal load scheduling recommendation."""
    timestamp: datetime
    device_type: str
    optimal_start_time: datetime
    duration_hours: float
    power_rating: float
    reason: str
    savings_potential: float
    confidence: float


@dataclass
class OptimizationPlan:
    """Alias for EnergyOptimizationPlan for backward compatibility."""
    timestamp: datetime
    daily_recommendations: List[OptimizationRecommendation]
    load_schedules: List[LoadSchedule]
    battery_strategy: Dict[str, Any]
    solar_utilization_score: float
    potential_daily_savings: float
    plan_confidence: float
    risk_assessment: Dict[str, float]


@dataclass
class EnergyOptimizationPlan:
    """Comprehensive energy optimization plan."""
    timestamp: datetime
    daily_recommendations: List[OptimizationRecommendation]
    load_schedules: List[LoadSchedule]
    battery_strategy: Dict[str, Any]
    solar_utilization_score: float
    potential_daily_savings: float
    plan_confidence: float
    risk_assessment: Dict[str, float]


class UsageOptimizer:
    """
    Advanced usage optimization engine that provides intelligent recommendations
    for energy management based on predictions and patterns.
    """
    
    def __init__(self, db_manager: DatabaseManager = None):
        """Initialize usage optimizer."""
        self.db_manager = db_manager or DatabaseManager()
        self.battery_predictor = BatteryPredictor(db_manager)
        self.weather_analyzer = WeatherAnalyzer(db_manager)
        
        # Configuration
        self.optimization_horizon = 24  # hours
        self.min_battery_reserve = float(os.getenv('BATTERY_MIN_SOC', '15.0'))
        self.peak_tariff_hours = [(17, 20), (6, 9)]  # Peak tariff periods
        self.off_peak_hours = [(22, 6)]  # Off-peak periods
        
        # Device power ratings (kW)
        self.device_ratings = {
            'geyser': float(os.getenv('GEYSER_POWER_RATING', '3.0')),
            'pool_pump': 1.5,
            'washing_machine': 2.0,
            'dishwasher': 1.8,
            'air_conditioner': 3.5,
            'electric_vehicle': 7.0
        }
        
        # Optimization weights
        self.optimization_weights = {
            'cost_savings': 0.4,
            'battery_health': 0.3,
            'solar_utilization': 0.2,
            'convenience': 0.1
        }
        
        logger.info("Usage optimizer initialized")
    
    async def generate_optimization_plan(self) -> EnergyOptimizationPlan:
        """Generate comprehensive daily optimization plan."""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Get predictions and analysis
            battery_pred = await self.battery_predictor.predict_battery_behavior(24)
            solar_forecast = await self.weather_analyzer.generate_solar_forecast(24)
            
            # Generate recommendations
            recommendations = await self._generate_daily_recommendations(
                battery_pred, solar_forecast
            )
            
            # Create load schedules
            load_schedules = await self._create_optimal_load_schedules(
                battery_pred, solar_forecast
            )
            
            # Develop battery strategy
            battery_strategy = await self._develop_battery_strategy(
                battery_pred, solar_forecast
            )
            
            # Calculate metrics
            solar_utilization = await self._calculate_solar_utilization_score(
                solar_forecast, load_schedules
            )
            
            potential_savings = await self._calculate_potential_savings(
                recommendations, load_schedules
            )
            
            plan_confidence = await self._calculate_plan_confidence(
                battery_pred, solar_forecast, recommendations
            )
            
            risk_assessment = await self._assess_optimization_risks(
                battery_pred, solar_forecast, load_schedules
            )
            
            return EnergyOptimizationPlan(
                timestamp=current_time,
                daily_recommendations=recommendations,
                load_schedules=load_schedules,
                battery_strategy=battery_strategy,
                solar_utilization_score=solar_utilization,
                potential_daily_savings=potential_savings,
                plan_confidence=plan_confidence,
                risk_assessment=risk_assessment
            )
            
        except Exception as e:
            logger.error(f"Error generating optimization plan: {e}")
            return self._create_empty_plan()
    
    async def optimize_device_usage(self, device_type: str, duration_hours: float) -> LoadSchedule:
        """Optimize usage timing for specific device."""
        try:
            if device_type not in self.device_ratings:
                logger.warning(f"Unknown device type: {device_type}")
                return self._create_empty_schedule(device_type)
            
            power_rating = self.device_ratings[device_type]
            
            # Get predictions
            battery_pred = await self.battery_predictor.predict_battery_behavior(24)
            solar_forecast = await self.weather_analyzer.generate_solar_forecast(24)
            
            # Find optimal time window
            optimal_time = await self._find_optimal_time_window(
                power_rating, duration_hours, battery_pred, solar_forecast
            )
            
            # Calculate savings and confidence
            savings = await self._calculate_device_savings(
                device_type, optimal_time, duration_hours, power_rating
            )
            
            confidence = await self._calculate_schedule_confidence(
                optimal_time, battery_pred, solar_forecast
            )
            
            # Generate reason
            reason = await self._generate_scheduling_reason(
                optimal_time, device_type, battery_pred, solar_forecast
            )
            
            return LoadSchedule(
                timestamp=datetime.now(timezone.utc),
                device_type=device_type,
                optimal_start_time=optimal_time,
                duration_hours=duration_hours,
                power_rating=power_rating,
                reason=reason,
                savings_potential=savings,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error optimizing device usage for {device_type}: {e}")
            return self._create_empty_schedule(device_type)
    
    async def _generate_daily_recommendations(self, battery_pred, solar_forecast):
        """Generate daily optimization recommendations."""
        recommendations = []
        current_time = datetime.now(timezone.utc)
        
        # Battery management recommendations
        if battery_pred.depletion_risk_score > 0.7:
            recommendations.append(OptimizationRecommendation(
                id=f"battery_risk_{current_time.hour}",
                type="battery_management",
                priority="critical",
                title="Critical Battery Management",
                description=f"High depletion risk ({battery_pred.depletion_risk_score:.1%})",
                potential_savings=2.0,  # kWh preserved
                confidence=battery_pred.confidence_score,
                time_window=(current_time, current_time + timedelta(hours=4)),
                actions=[
                    "Immediately reduce non-essential loads",
                    "Defer high-power appliances",
                    "Monitor battery levels closely"
                ],
                impact_score=90
            ))
        
        # Solar utilization recommendations
        if solar_forecast.forecast_4h > 2.0:  # Good solar expected
            recommendations.append(OptimizationRecommendation(
                id=f"solar_utilization_{current_time.hour}",
                type="solar_utilization",
                priority="medium",
                title="Solar Power Opportunity",
                description=f"Excellent solar forecast: {solar_forecast.forecast_4h:.1f}kW",
                potential_savings=1.5,
                confidence=solar_forecast.confidence_score,
                time_window=(current_time + timedelta(hours=1), current_time + timedelta(hours=5)),
                actions=[
                    "Schedule geyser heating",
                    "Run washing machine/dishwasher",
                    "Charge electric vehicle if available"
                ],
                impact_score=75
            ))
        
        # Peak tariff avoidance
        next_peak_start = await self._find_next_peak_period(current_time)
        if next_peak_start and (next_peak_start - current_time).total_seconds() < 7200:  # Within 2 hours
            recommendations.append(OptimizationRecommendation(
                id=f"peak_avoidance_{current_time.hour}",
                type="load_shift",
                priority="high",
                title="Peak Tariff Avoidance",
                description=f"Peak tariff starts at {next_peak_start.strftime('%H:%M')}",
                potential_savings=0.8,  # Cost savings
                confidence=0.9,
                time_window=(current_time, next_peak_start),
                actions=[
                    "Complete high-power tasks before peak period",
                    "Avoid using air conditioning during peak",
                    "Pre-heat water before peak hours"
                ],
                impact_score=80
            ))
        
        # Load balancing recommendations
        if battery_pred.charging_opportunity_score > 0.6:
            recommendations.append(OptimizationRecommendation(
                id=f"load_balance_{current_time.hour}",
                type="load_shift",
                priority="low",
                title="Load Balancing Opportunity",
                description="Good conditions for increased consumption",
                potential_savings=1.2,
                confidence=battery_pred.confidence_score,
                time_window=(current_time, current_time + timedelta(hours=6)),
                actions=[
                    "Consider running pool pump",
                    "Good time for appliance maintenance cycles",
                    "Schedule backup heating if needed"
                ],
                impact_score=60
            ))
        
        return sorted(recommendations, key=lambda x: x.impact_score, reverse=True)
    
    async def _create_optimal_load_schedules(self, battery_pred, solar_forecast):
        """Create optimal schedules for common devices."""
        schedules = []
        
        # Geyser optimization
        geyser_schedule = await self.optimize_device_usage('geyser', 2.0)
        schedules.append(geyser_schedule)
        
        # Washing machine optimization
        washing_schedule = await self.optimize_device_usage('washing_machine', 1.5)
        schedules.append(washing_schedule)
        
        # Pool pump optimization (if applicable)
        pool_schedule = await self.optimize_device_usage('pool_pump', 4.0)
        schedules.append(pool_schedule)
        
        return schedules
    
    async def _develop_battery_strategy(self, battery_pred, solar_forecast):
        """Develop optimal battery management strategy."""
        strategy = {
            'current_status': {
                'soc': battery_pred.current_soc,
                'risk_level': self._categorize_risk(battery_pred.depletion_risk_score),
                'opportunity_level': self._categorize_opportunity(battery_pred.charging_opportunity_score)
            },
            'charging_windows': [],
            'conservation_periods': [],
            'utilization_recommendations': []
        }
        
        current_time = datetime.now(timezone.utc)
        
        # Identify charging windows
        for hour_offset in range(24):
            target_time = current_time + timedelta(hours=hour_offset)
            hour = target_time.hour
            
            # Solar charging window
            if 9 <= hour <= 15 and solar_forecast.forecast_4h > 1.5:
                strategy['charging_windows'].append({
                    'start': target_time,
                    'duration': 4,
                    'type': 'solar_charging',
                    'priority': 'high'
                })
        
        # Identify conservation periods
        if battery_pred.depletion_risk_score > 0.5:
            strategy['conservation_periods'].append({
                'start': current_time,
                'duration': 8,
                'type': 'risk_mitigation',
                'priority': 'high'
            })
        
        # Add utilization recommendations
        if battery_pred.current_soc > 80:
            strategy['utilization_recommendations'].append(
                'Battery well charged - good time for high-power loads'
            )
        elif battery_pred.current_soc < 30:
            strategy['utilization_recommendations'].append(
                'Battery low - conserve power and avoid non-essential loads'
            )
        
        return strategy
    
    def _categorize_risk(self, risk_score):
        """Categorize depletion risk level."""
        if risk_score > 0.8:
            return 'critical'
        elif risk_score > 0.6:
            return 'high'
        elif risk_score > 0.3:
            return 'medium'
        else:
            return 'low'
    
    def _categorize_opportunity(self, opportunity_score):
        """Categorize charging opportunity level."""
        if opportunity_score > 0.8:
            return 'excellent'
        elif opportunity_score > 0.6:
            return 'good'
        elif opportunity_score > 0.3:
            return 'moderate'
        else:
            return 'poor'
    
    async def _find_optimal_time_window(self, power_rating, duration_hours, battery_pred, solar_forecast):
        """Find optimal time window for device operation."""
        current_time = datetime.now(timezone.utc)
        best_time = current_time
        best_score = 0
        
        # Evaluate each possible start time in the next 24 hours
        for hour_offset in range(24):
            candidate_time = current_time + timedelta(hours=hour_offset)
            score = await self._score_time_window(
                candidate_time, duration_hours, power_rating, battery_pred, solar_forecast
            )
            
            if score > best_score:
                best_score = score
                best_time = candidate_time
        
        return best_time
    
    async def _score_time_window(self, start_time, duration_hours, power_rating, battery_pred, solar_forecast):
        """Score a time window for device operation."""
        score = 0
        hour = start_time.hour
        
        # Solar availability bonus
        if 10 <= hour <= 14:  # Peak solar hours
            score += 40
        elif 8 <= hour <= 16:  # Good solar hours
            score += 20
        
        # Avoid peak tariff hours
        if self._is_peak_tariff_hour(hour):
            score -= 30
        
        # Off-peak bonus
        if self._is_off_peak_hour(hour):
            score += 15
        
        # Battery state consideration
        if battery_pred.current_soc > 70:
            score += 25  # Good battery level
        elif battery_pred.current_soc < 30:
            score -= 25  # Low battery level
        
        # Solar forecast consideration
        if solar_forecast.forecast_4h > power_rating:
            score += 30  # Solar can cover the load
        
        # Convenience factors (avoid very early/late hours for most devices)
        if 6 <= hour <= 22:
            score += 10
        
        return max(0, score)
    
    def _is_peak_tariff_hour(self, hour):
        """Check if hour is in peak tariff period."""
        for start, end in self.peak_tariff_hours:
            if start <= hour < end:
                return True
        return False
    
    def _is_off_peak_hour(self, hour):
        """Check if hour is in off-peak period."""
        for start, end in self.off_peak_hours:
            if start <= hour < end or (start > end and (hour >= start or hour < end)):
                return True
        return False
    
    async def _find_next_peak_period(self, current_time):
        """Find the next peak tariff period."""
        current_hour = current_time.hour
        
        for start, end in self.peak_tariff_hours:
            if current_hour < start:
                return current_time.replace(hour=start, minute=0, second=0, microsecond=0)
            elif start > end and current_hour >= start:
                # Next day morning peak
                next_day = current_time + timedelta(days=1)
                return next_day.replace(hour=6, minute=0, second=0, microsecond=0)
        
        # Default to next day first peak
        next_day = current_time + timedelta(days=1)
        return next_day.replace(hour=6, minute=0, second=0, microsecond=0)
    
    async def _calculate_solar_utilization_score(self, solar_forecast, load_schedules):
        """Calculate solar utilization optimization score."""
        if not load_schedules:
            return 50  # Baseline
        
        utilization_score = 0
        total_load_during_solar = 0
        
        for schedule in load_schedules:
            start_hour = schedule.optimal_start_time.hour
            if 8 <= start_hour <= 16:  # During solar hours
                total_load_during_solar += schedule.power_rating * schedule.duration_hours
        
        # Compare with available solar
        if solar_forecast.daily_total_kwh > 0:
            utilization_ratio = min(1.0, total_load_during_solar / solar_forecast.daily_total_kwh)
            utilization_score = utilization_ratio * 100
        
        return min(100, utilization_score)
    
    async def _calculate_potential_savings(self, recommendations, load_schedules):
        """Calculate potential daily savings from optimization."""
        savings = 0
        
        # Savings from recommendations
        for rec in recommendations:
            savings += rec.potential_savings * rec.confidence
        
        # Savings from optimal scheduling
        for schedule in load_schedules:
            savings += schedule.savings_potential * schedule.confidence
        
        return savings
    
    async def _calculate_plan_confidence(self, battery_pred, solar_forecast, recommendations):
        """Calculate overall plan confidence."""
        confidence_factors = [
            battery_pred.confidence_score * 0.4,
            solar_forecast.confidence_score * 0.3,
            min(1.0, len(recommendations) / 5) * 0.3  # More recommendations = higher confidence
        ]
        
        return sum(confidence_factors)
    
    async def _assess_optimization_risks(self, battery_pred, solar_forecast, load_schedules):
        """Assess risks in the optimization plan."""
        risks = {
            'battery_depletion': battery_pred.depletion_risk_score,
            'weather_dependency': 1 - solar_forecast.confidence_score,
            'schedule_conflict': 0.0,  # Could be calculated based on overlapping schedules
            'grid_dependency': 0.3 if battery_pred.current_soc < 50 else 0.1
        }
        
        return risks
    
    async def _calculate_device_savings(self, device_type, optimal_time, duration_hours, power_rating):
        """Calculate potential savings for device scheduling."""
        # Simplified savings calculation
        base_savings = 0.5  # Base savings from optimization
        
        # Time-based adjustments
        hour = optimal_time.hour
        if 10 <= hour <= 14:  # Solar hours
            base_savings += 0.3
        if self._is_peak_tariff_hour(hour):
            base_savings -= 0.2
        if self._is_off_peak_hour(hour):
            base_savings += 0.2
        
        return max(0, base_savings)
    
    async def _calculate_schedule_confidence(self, optimal_time, battery_pred, solar_forecast):
        """Calculate confidence in the schedule."""
        confidence = 0.5  # Base confidence
        
        # Add confidence based on predictions
        confidence += battery_pred.confidence_score * 0.3
        confidence += solar_forecast.confidence_score * 0.2
        
        return min(1.0, confidence)
    
    async def _generate_scheduling_reason(self, optimal_time, device_type, battery_pred, solar_forecast):
        """Generate reason for the scheduling recommendation."""
        hour = optimal_time.hour
        reasons = []
        
        if 10 <= hour <= 14:
            reasons.append("peak solar generation")
        if not self._is_peak_tariff_hour(hour):
            reasons.append("off-peak tariff")
        if battery_pred.current_soc > 70:
            reasons.append("good battery level")
        if solar_forecast.forecast_4h > 2.0:
            reasons.append("excellent solar forecast")
        
        if not reasons:
            return "Optimal based on current conditions"
        
        return f"Scheduled during {', '.join(reasons)}"
    
    def _create_empty_plan(self):
        """Create empty optimization plan."""
        return EnergyOptimizationPlan(
            timestamp=datetime.now(timezone.utc),
            daily_recommendations=[],
            load_schedules=[],
            battery_strategy={},
            solar_utilization_score=0.0,
            potential_daily_savings=0.0,
            plan_confidence=0.0,
            risk_assessment={}
        )
    
    def _create_empty_schedule(self, device_type):
        """Create empty load schedule."""
        current_time = datetime.now(timezone.utc)
        return LoadSchedule(
            timestamp=current_time,
            device_type=device_type,
            optimal_start_time=current_time,
            duration_hours=0.0,
            power_rating=0.0,
            reason="No optimization data available",
            savings_potential=0.0,
            confidence=0.0
        )


# Test function
async def test_usage_optimizer():
    """Test usage optimizer functionality."""
    db_manager = DatabaseManager()
    if not await db_manager.connect():
        print("Could not connect to database")
        return
    
    optimizer = UsageOptimizer(db_manager)
    
    print("Testing usage optimizer...")
    
    # Test optimization plan
    plan = await optimizer.generate_optimization_plan()
    print(f"Optimization Plan - Confidence: {plan.plan_confidence:.2f}")
    print(f"  Recommendations: {len(plan.daily_recommendations)}")
    print(f"  Load Schedules: {len(plan.load_schedules)}")
    print(f"  Potential Savings: {plan.potential_daily_savings:.2f}")
    
    # Test device optimization
    geyser_schedule = await optimizer.optimize_device_usage('geyser', 2.0)
    print(f"\nGeyser Schedule - Optimal Time: {geyser_schedule.optimal_start_time.strftime('%H:%M')}")
    print(f"  Reason: {geyser_schedule.reason}")
    print(f"  Savings: {geyser_schedule.savings_potential:.2f}")
    
    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(test_usage_optimizer())
