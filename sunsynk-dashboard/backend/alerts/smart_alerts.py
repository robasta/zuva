"""
Additional Smart Alert Types - Phase 5
Implementation of various intelligent alert types beyond core energy deficit alerts
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass

from .models import AlertConfiguration, AlertCondition, AlertType, AlertSeverity

logger = logging.getLogger(__name__)

@dataclass
class PeakDemandEvent:
    """Peak demand event data"""
    timestamp: datetime
    consumption_spike: float  # kW
    solar_generation: float  # kW
    deficit: float  # kW
    duration_minutes: int
    severity: str

@dataclass
class WeatherWarningEvent:
    """Weather warning event data"""
    timestamp: datetime
    weather_type: str  # storm, cloudy, etc.
    impact_severity: str
    expected_generation_loss: float  # %
    hours_until_impact: float
    duration_hours: float

@dataclass
class OptimizationOpportunity:
    """Battery/grid optimization opportunity"""
    timestamp: datetime
    opportunity_type: str
    potential_savings: float  # R
    action_required: str
    time_window_hours: float
    confidence: float

class PeakDemandAlertGenerator:
    """Generate alerts for consumption spikes during low solar generation"""
    
    def __init__(self):
        self.consumption_history: List[Tuple[datetime, float]] = []
        self.solar_history: List[Tuple[datetime, float]] = []
        self.demand_events: List[PeakDemandEvent] = []
    
    def add_data(self, timestamp: datetime, consumption: float, solar_power: float):
        """Add consumption and solar data"""
        self.consumption_history.append((timestamp, consumption))
        self.solar_history.append((timestamp, solar_power))
        
        # Keep last 24 hours
        cutoff = timestamp - timedelta(hours=24)
        self.consumption_history = [(t, c) for t, c in self.consumption_history if t >= cutoff]
        self.solar_history = [(t, s) for t, s in self.solar_history if t >= cutoff]
    
    def detect_peak_demand_events(self, config: AlertConfiguration) -> List[AlertCondition]:
        """Detect peak demand events that warrant alerts"""
        if len(self.consumption_history) < 10:
            return []
        
        alerts = []
        current_time = datetime.now()
        
        # Calculate rolling averages
        recent_consumption = [c for t, c in self.consumption_history[-10:]]  # Last 10 readings
        recent_solar = [s for t, s in self.solar_history[-10:]]  # Last 10 readings
        
        if not recent_consumption or not recent_solar:
            return []
        
        current_consumption = recent_consumption[-1]
        current_solar = recent_solar[-1]
        avg_consumption = np.mean(recent_consumption[:-1])  # Exclude current reading
        
        # Detect spike (consumption 50% above recent average)
        consumption_spike = current_consumption - avg_consumption
        spike_threshold = avg_consumption * 0.5
        
        if consumption_spike > spike_threshold:
            # Check if this occurs during low solar generation
            if current_solar < 2.0:  # Less than 2kW generation
                deficit = current_consumption - current_solar
                
                if deficit > config.energy_thresholds.deficit_threshold_kw:
                    # Calculate severity
                    if consumption_spike > avg_consumption:
                        severity = AlertSeverity.HIGH
                    elif consumption_spike > avg_consumption * 0.75:
                        severity = AlertSeverity.MEDIUM
                    else:
                        severity = AlertSeverity.LOW
                    
                    alert = AlertCondition(
                        condition_id=f"peak_demand_{current_time.isoformat()}",
                        alert_type=AlertType.PEAK_DEMAND,
                        description=f"Peak demand spike of {consumption_spike:.2f}kW detected during low solar generation ({current_solar:.2f}kW). Current deficit: {deficit:.2f}kW",
                        is_daylight=6 <= current_time.hour <= 18,
                        energy_deficit=deficit,
                        battery_level=0,  # Would get from actual battery data
                        battery_loss=0,
                        weather_conditions={},
                        confidence=0.85,
                        severity=severity,
                        timestamp=current_time
                    )
                    alerts.append(alert)
        
        return alerts

class WeatherWarningAlertGenerator:
    """Generate alerts for incoming weather events that may impact solar generation"""
    
    def __init__(self):
        self.weather_forecasts: List[Dict] = []
        self.warning_events: List[WeatherWarningEvent] = []
    
    async def check_weather_warnings(self, config: AlertConfiguration) -> List[AlertCondition]:
        """Check for weather warnings that warrant alerts"""
        try:
            # This would integrate with weather service
            # For now, simulate weather warning detection
            current_time = datetime.now()
            alerts = []
            
            # Simulate storm warning
            import random
            if random.random() < 0.1:  # 10% chance of simulated weather warning
                hours_until = random.uniform(2, 12)
                generation_loss = random.uniform(40, 80)
                
                alert = AlertCondition(
                    condition_id=f"weather_warning_{current_time.isoformat()}",
                    alert_type=AlertType.WEATHER_WARNING,
                    description=f"Weather warning: Storm system approaching in {hours_until:.1f} hours. Expected {generation_loss:.0f}% reduction in solar generation.",
                    is_daylight=True,
                    energy_deficit=0,
                    battery_level=0,
                    battery_loss=0,
                    weather_conditions={
                        'warning_type': 'storm',
                        'hours_until_impact': hours_until,
                        'expected_loss_percentage': generation_loss
                    },
                    confidence=0.75,
                    severity=AlertSeverity.MEDIUM if generation_loss > 60 else AlertSeverity.LOW,
                    timestamp=current_time
                )
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking weather warnings: {e}")
            return []

class BatteryOptimizationAlertGenerator:
    """Generate alerts for battery optimization opportunities"""
    
    def __init__(self):
        self.optimization_history: List[OptimizationOpportunity] = []
    
    def check_optimization_opportunities(self, config: AlertConfiguration, 
                                       current_data: Dict) -> List[AlertCondition]:
        """Check for battery optimization opportunities"""
        alerts = []
        current_time = datetime.now()
        
        try:
            battery_level = current_data.get('battery_level', 50)
            solar_power = current_data.get('solar_power', 0)
            consumption = current_data.get('consumption', 2)
            hour = current_time.hour
            
            # Morning optimization: Battery should be charged before peak hours
            if 8 <= hour <= 10 and battery_level < 60 and solar_power > 3:
                alert = AlertCondition(
                    condition_id=f"battery_optimization_{current_time.isoformat()}",
                    alert_type=AlertType.BATTERY_OPTIMIZATION,
                    description=f"Battery optimization opportunity: Charge battery to 80%+ before peak hours. Current level: {battery_level:.1f}%, solar generation: {solar_power:.2f}kW",
                    is_daylight=True,
                    energy_deficit=0,
                    battery_level=battery_level,
                    battery_loss=0,
                    weather_conditions={},
                    confidence=0.8,
                    severity=AlertSeverity.LOW,
                    timestamp=current_time
                )
                alerts.append(alert)
            
            # Evening optimization: Use battery instead of grid
            elif 17 <= hour <= 20 and battery_level > 40 and consumption > solar_power:
                deficit = consumption - solar_power
                if deficit > 1:  # Significant grid usage
                    alert = AlertCondition(
                        condition_id=f"battery_optimization_{current_time.isoformat()}",
                        alert_type=AlertType.BATTERY_OPTIMIZATION,
                        description=f"Battery optimization: Switch to battery power to avoid {deficit:.2f}kW grid consumption. Battery level: {battery_level:.1f}%",
                        is_daylight=False,
                        energy_deficit=deficit,
                        battery_level=battery_level,
                        battery_loss=0,
                        weather_conditions={},
                        confidence=0.9,
                        severity=AlertSeverity.LOW,
                        timestamp=current_time
                    )
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking battery optimization: {e}")
            return []

class GridExportOpportunityAlertGenerator:
    """Generate alerts for grid export opportunities during excess generation"""
    
    def __init__(self):
        self.export_opportunities: List[Dict] = []
    
    def check_export_opportunities(self, config: AlertConfiguration,
                                 current_data: Dict) -> List[AlertCondition]:
        """Check for profitable grid export opportunities"""
        alerts = []
        current_time = datetime.now()
        
        try:
            solar_power = current_data.get('solar_power', 0)
            consumption = current_data.get('consumption', 2)
            battery_level = current_data.get('battery_level', 50)
            hour = current_time.hour
            
            # Check for excess generation during peak tariff hours
            excess = solar_power - consumption
            
            if excess > 1.0 and battery_level > 80:  # Significant excess and battery full
                # Simulate peak tariff hours (would use real tariff data)
                is_peak_tariff = 10 <= hour <= 16  # Weekday peak hours
                
                if is_peak_tariff:
                    potential_revenue = excess * 1.50  # R1.50/kWh feed-in rate
                    
                    alert = AlertCondition(
                        condition_id=f"grid_export_{current_time.isoformat()}",
                        alert_type=AlertType.GRID_EXPORT_OPPORTUNITY,
                        description=f"Grid export opportunity: {excess:.2f}kW excess generation during peak tariff period. Potential revenue: R{potential_revenue:.2f}/hour",
                        is_daylight=True,
                        energy_deficit=-excess,  # Negative indicates surplus
                        battery_level=battery_level,
                        battery_loss=0,
                        weather_conditions={},
                        confidence=0.85,
                        severity=AlertSeverity.LOW,
                        timestamp=current_time
                    )
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking export opportunities: {e}")
            return []

class CostOptimizationAlertGenerator:
    """Generate alerts for electricity cost optimization opportunities"""
    
    def __init__(self):
        self.cost_opportunities: List[Dict] = []
    
    def check_cost_optimization(self, config: AlertConfiguration,
                              current_data: Dict) -> List[AlertCondition]:
        """Check for cost optimization opportunities"""
        alerts = []
        current_time = datetime.now()
        
        try:
            consumption = current_data.get('consumption', 2)
            battery_level = current_data.get('battery_level', 50)
            hour = current_time.hour
            
            # Time-of-use optimization
            is_peak_rate = 17 <= hour <= 20  # Peak rate hours
            is_off_peak = 22 <= hour or hour <= 6  # Off-peak hours
            
            if is_peak_rate and consumption > 2 and battery_level > 30:
                potential_savings = (consumption - 1) * 2.50  # Peak rate R2.50/kWh
                
                alert = AlertCondition(
                    condition_id=f"cost_optimization_{current_time.isoformat()}",
                    alert_type=AlertType.COST_OPTIMIZATION,
                    description=f"Cost optimization: Reduce grid usage during peak rates. Switch to battery or reduce consumption. Potential savings: R{potential_savings:.2f}/hour",
                    is_daylight=False,
                    energy_deficit=consumption,
                    battery_level=battery_level,
                    battery_loss=0,
                    weather_conditions={},
                    confidence=0.9,
                    severity=AlertSeverity.LOW,
                    timestamp=current_time
                )
                alerts.append(alert)
            
            elif is_off_peak and battery_level < 50:
                # Opportunity to charge battery at off-peak rates
                alert = AlertCondition(
                    condition_id=f"cost_optimization_{current_time.isoformat()}",
                    alert_type=AlertType.COST_OPTIMIZATION,
                    description=f"Cost optimization: Charge battery during off-peak rates (R0.85/kWh). Current battery: {battery_level:.1f}%",
                    is_daylight=False,
                    energy_deficit=0,
                    battery_level=battery_level,
                    battery_loss=0,
                    weather_conditions={},
                    confidence=0.8,
                    severity=AlertSeverity.LOW,
                    timestamp=current_time
                )
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking cost optimization: {e}")
            return []

class MaintenanceReminderAlertGenerator:
    """Generate maintenance reminder alerts based on performance patterns"""
    
    def __init__(self):
        self.performance_history: List[Dict] = []
        self.last_maintenance_check = datetime.now() - timedelta(days=30)
    
    def check_maintenance_requirements(self, config: AlertConfiguration,
                                     current_data: Dict) -> List[AlertCondition]:
        """Check for maintenance requirements based on performance degradation"""
        alerts = []
        current_time = datetime.now()
        
        try:
            # Monthly maintenance check
            if (current_time - self.last_maintenance_check).days >= 30:
                solar_power = current_data.get('solar_power', 0)
                expected_power = 4.5  # Expected peak power for system
                
                # Check if performance is degraded
                if 10 <= current_time.hour <= 14:  # Peak hours
                    if solar_power < expected_power * 0.8:  # 20% below expected
                        performance_ratio = (solar_power / expected_power) * 100
                        
                        alert = AlertCondition(
                            condition_id=f"maintenance_{current_time.isoformat()}",
                            alert_type=AlertType.MAINTENANCE_REMINDER,
                            description=f"Maintenance check recommended: Solar performance at {performance_ratio:.0f}% of expected. Consider panel cleaning and system inspection.",
                            is_daylight=True,
                            energy_deficit=0,
                            battery_level=current_data.get('battery_level', 50),
                            battery_loss=0,
                            weather_conditions={},
                            confidence=0.7,
                            severity=AlertSeverity.LOW,
                            timestamp=current_time
                        )
                        alerts.append(alert)
                        
                        self.last_maintenance_check = current_time
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking maintenance requirements: {e}")
            return []

class SmartAlertEngine:
    """Coordinated engine for all smart alert types"""
    
    def __init__(self):
        self.peak_demand_generator = PeakDemandAlertGenerator()
        self.weather_warning_generator = WeatherWarningAlertGenerator()
        self.battery_optimization_generator = BatteryOptimizationAlertGenerator()
        self.grid_export_generator = GridExportOpportunityAlertGenerator()
        self.cost_optimization_generator = CostOptimizationAlertGenerator()
        self.maintenance_generator = MaintenanceReminderAlertGenerator()
    
    async def generate_all_smart_alerts(self, config: AlertConfiguration,
                                      current_data: Dict) -> List[AlertCondition]:
        """Generate all types of smart alerts"""
        all_alerts = []
        
        try:
            # Add current data to generators
            timestamp = current_data.get('timestamp', datetime.now())
            consumption = current_data.get('consumption', 0)
            solar_power = current_data.get('solar_power', 0)
            
            self.peak_demand_generator.add_data(timestamp, consumption, solar_power)
            
            # Generate alerts from all generators
            all_alerts.extend(self.peak_demand_generator.detect_peak_demand_events(config))
            all_alerts.extend(await self.weather_warning_generator.check_weather_warnings(config))
            all_alerts.extend(self.battery_optimization_generator.check_optimization_opportunities(config, current_data))
            all_alerts.extend(self.grid_export_generator.check_export_opportunities(config, current_data))
            all_alerts.extend(self.cost_optimization_generator.check_cost_optimization(config, current_data))
            all_alerts.extend(self.maintenance_generator.check_maintenance_requirements(config, current_data))
            
            # Filter alerts based on configuration
            filtered_alerts = self._filter_alerts_by_config(all_alerts, config)
            
            return filtered_alerts
            
        except Exception as e:
            logger.error(f"Error generating smart alerts: {e}")
            return []
    
    def _filter_alerts_by_config(self, alerts: List[AlertCondition], 
                                config: AlertConfiguration) -> List[AlertCondition]:
        """Filter alerts based on configuration preferences"""
        filtered = []
        
        for alert in alerts:
            # Filter by severity
            severity_order = {
                AlertSeverity.LOW: 0,
                AlertSeverity.MEDIUM: 1,
                AlertSeverity.HIGH: 2,
                AlertSeverity.CRITICAL: 3
            }
            
            if severity_order[alert.severity] >= severity_order[config.severity_filter]:
                filtered.append(alert)
        
        return filtered

# Global smart alert engine instance
smart_alert_engine = SmartAlertEngine()