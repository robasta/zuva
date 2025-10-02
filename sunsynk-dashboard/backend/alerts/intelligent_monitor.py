"""
Intelligent Alert Monitor - Phase 1 Core Implementation
Provides daylight-aware energy deficit detection with battery monitoring
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import pytz
try:
    from astral import LocationInfo
    from astral.sun import sun
    ASTRAL_AVAILABLE = True
except ImportError:
    ASTRAL_AVAILABLE = False
    LocationInfo = None
    sun = None

import numpy as np
from dataclasses import dataclass

from .models import (
    AlertConfiguration, AlertCondition, AlertInstance, AlertType, 
    AlertSeverity, AlertState, DaylightConfiguration
)

# Import smart alerts
try:
    from .smart_alerts import smart_alert_engine
    SMART_ALERTS_AVAILABLE = True
except ImportError:
    SMART_ALERTS_AVAILABLE = False
    smart_alert_engine = None

logger = logging.getLogger(__name__)

@dataclass
class EnergyData:
    """Real-time energy data structure"""
    timestamp: datetime
    solar_power: float  # kW
    consumption: float  # kW
    battery_level: float  # %
    grid_consumption: float  # kW

@dataclass
class DaylightInfo:
    """Daylight calculation results"""
    is_daylight: bool
    sunrise: datetime
    sunset: datetime
    day_length_hours: float
    season: str  # 'summer', 'winter', 'autumn', 'spring'
    daylight_buffer_applied: int  # minutes

class DaylightCalculator:
    """Accurate sunrise/sunset calculations with seasonal adjustments"""
    
    def __init__(self, config: DaylightConfiguration):
        self.config = config
        if ASTRAL_AVAILABLE:
            self.location = LocationInfo(
                name="Randburg",
                region="ZA", 
                timezone=config.timezone,
                latitude=config.latitude,
                longitude=config.longitude
            )
        self.timezone = pytz.timezone(config.timezone)
    
    def get_daylight_info(self, date: datetime = None) -> DaylightInfo:
        """Get comprehensive daylight information for a given date"""
        if date is None:
            date = datetime.now(self.timezone)
        elif date.tzinfo is None:
            date = self.timezone.localize(date)
        
        if ASTRAL_AVAILABLE:
            try:
                # Calculate sun times
                s = sun(self.location.observer, date=date.date())
                sunrise = s['sunrise'].astimezone(self.timezone)
                sunset = s['sunset'].astimezone(self.timezone)
                
                # Determine season and appropriate buffer
                season = self._get_season(date)
                buffer_minutes = self._get_seasonal_buffer(season)
                
                # Apply daylight buffer
                sunrise_buffered = sunrise - timedelta(minutes=buffer_minutes)
                sunset_buffered = sunset + timedelta(minutes=buffer_minutes)
                
                # Check if current time is within daylight hours
                is_daylight = sunrise_buffered <= date <= sunset_buffered
                
                # Calculate day length
                day_length_hours = (sunset - sunrise).total_seconds() / 3600
                
                return DaylightInfo(
                    is_daylight=is_daylight,
                    sunrise=sunrise,
                    sunset=sunset,
                    day_length_hours=day_length_hours,
                    season=season,
                    daylight_buffer_applied=buffer_minutes
                )
                
            except Exception as e:
                logger.error(f"Daylight calculation error: {e}")
        
        # Fallback to simple time-based check
        current_hour = date.hour
        is_daylight = 6 <= current_hour <= 18
        
        return DaylightInfo(
            is_daylight=is_daylight,
            sunrise=date.replace(hour=6, minute=0, second=0),
            sunset=date.replace(hour=18, minute=0, second=0),
            day_length_hours=12.0,
            season=self._get_season(date),
            daylight_buffer_applied=self.config.daylight_buffer_minutes
        )
    
    def _get_season(self, date: datetime) -> str:
        """Determine season based on date (Southern Hemisphere)"""
        month = date.month
        if month in [12, 1, 2]:
            return 'summer'
        elif month in [3, 4, 5]:
            return 'autumn'
        elif month in [6, 7, 8]:
            return 'winter'
        else:
            return 'spring'
    
    def _get_seasonal_buffer(self, season: str) -> int:
        """Get appropriate daylight buffer for season"""
        if season == 'summer':
            return self.config.daylight_buffer_minutes + 15  # Longer summer days
        elif season == 'winter':
            return max(10, self.config.daylight_buffer_minutes - 10)  # Shorter winter days
        else:
            return self.config.daylight_buffer_minutes

class EnergyDeficitDetector:
    """Real-time energy balance monitoring and deficit detection"""
    
    def __init__(self):
        self.energy_history: List[EnergyData] = []
        self.max_history_length = 1440  # 24 hours of minute-by-minute data
    
    def add_energy_data(self, data: EnergyData):
        """Add new energy data point"""
        self.energy_history.append(data)
        
        # Maintain rolling window
        if len(self.energy_history) > self.max_history_length:
            self.energy_history = self.energy_history[-self.max_history_length:]
    
    def get_current_deficit(self, data: EnergyData) -> float:
        """Calculate current energy deficit in kW"""
        # Energy deficit = consumption - solar generation
        # Positive value indicates deficit (consuming more than generating)
        deficit = data.consumption - data.solar_power
        return max(0, deficit)  # Only report deficits, not surpluses
    
    def get_sustained_deficit(self, config: AlertConfiguration, current_time: datetime) -> Tuple[bool, float]:
        """Check if deficit has been sustained for configured duration"""
        if len(self.energy_history) < 2:
            return False, 0.0
        
        # Look back for the specified timeframe
        cutoff_time = current_time - timedelta(minutes=config.energy_thresholds.sustained_deficit_minutes)
        recent_data = [d for d in self.energy_history if d.timestamp >= cutoff_time]
        
        if len(recent_data) < 3:  # Need minimum data points
            return False, 0.0
        
        # Calculate average deficit over the period
        deficits = [self.get_current_deficit(d) for d in recent_data]
        avg_deficit = np.mean(deficits)
        
        # Check if sustained deficit exceeds threshold
        is_sustained = avg_deficit >= config.energy_thresholds.deficit_threshold_kw
        
        return is_sustained, avg_deficit

class BatteryMonitor:
    """Battery level monitoring and loss detection"""
    
    def __init__(self):
        self.battery_history: List[Tuple[datetime, float]] = []
        self.max_history_hours = 24
    
    def add_battery_data(self, timestamp: datetime, level: float):
        """Add battery level data point"""
        self.battery_history.append((timestamp, level))
        
        # Clean old data
        cutoff_time = timestamp - timedelta(hours=self.max_history_hours)
        self.battery_history = [(t, l) for t, l in self.battery_history if t >= cutoff_time]
    
    def get_battery_loss(self, config: AlertConfiguration, current_time: datetime) -> Tuple[bool, float]:
        """Calculate battery loss over the configured timeframe"""
        if len(self.battery_history) < 2:
            return False, 0.0
        
        # Find battery level at start of timeframe
        lookback_time = current_time - timedelta(minutes=config.battery_thresholds.loss_timeframe_minutes)
        
        # Find closest historical point to lookback time
        historical_point = None
        min_time_diff = float('inf')
        
        for timestamp, level in self.battery_history:
            time_diff = abs((timestamp - lookback_time).total_seconds())
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                historical_point = (timestamp, level)
        
        if not historical_point:
            return False, 0.0
        
        # Calculate loss
        historical_level = historical_point[1]
        current_level = self.battery_history[-1][1] if self.battery_history else 0
        
        battery_loss = historical_level - current_level
        loss_exceeds_threshold = battery_loss > config.battery_thresholds.max_loss_threshold
        
        return loss_exceeds_threshold, battery_loss
    
    def is_battery_critical(self, current_level: float, config: AlertConfiguration) -> Tuple[bool, str]:
        """Check if battery is at critical level"""
        if current_level <= config.battery_thresholds.critical_level:
            return True, f"Battery critically low at {current_level:.1f}%"
        elif current_level <= config.battery_thresholds.min_level_threshold:
            return True, f"Battery below minimum threshold at {current_level:.1f}%"
        else:
            return False, ""

class IntelligentAlertMonitor:
    """Main monitoring engine combining all detection components"""
    
    def __init__(self):
        self.daylight_calculator = None
        self.deficit_detector = EnergyDeficitDetector()
        self.battery_monitor = BatteryMonitor()
        self.active_alerts: Dict[str, AlertInstance] = {}
        self.monitoring_active = False
    
    def initialize(self, config: AlertConfiguration):
        """Initialize monitor with configuration"""
        self.daylight_calculator = DaylightCalculator(config.daylight_config)
        logger.info(f"Intelligent alert monitor initialized for user {config.user_id}")
    
    async def start_monitoring(self, config: AlertConfiguration):
        """Start continuous monitoring"""
        if not self.daylight_calculator:
            self.initialize(config)
        
        self.monitoring_active = True
        logger.info("Starting intelligent alert monitoring...")
        
        while self.monitoring_active:
            try:
                await self._monitoring_cycle(config)
                await asyncio.sleep(30)  # 30-second monitoring interval
            except Exception as e:
                logger.error(f"Monitoring cycle error: {e}")
                await asyncio.sleep(60)  # Longer delay on error
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring_active = False
        logger.info("Intelligent alert monitoring stopped")
    
    async def _monitoring_cycle(self, config: AlertConfiguration):
        """Single monitoring cycle"""
        current_time = datetime.now()
        
        # Get current energy data (this would integrate with your InfluxDB)
        energy_data = await self._get_current_energy_data()
        if not energy_data:
            return
        
        # Add to monitoring history
        self.deficit_detector.add_energy_data(energy_data)
        self.battery_monitor.add_battery_data(energy_data.timestamp, energy_data.battery_level)
        
        # Get daylight information
        daylight_info = self.daylight_calculator.get_daylight_info(current_time)
        
        # Only process alerts during daylight hours
        if not daylight_info.is_daylight:
            return
        
        # Check core alert conditions (energy deficit)
        alert_condition = await self._evaluate_alert_conditions(config, energy_data, daylight_info)
        
        if alert_condition and alert_condition.meets_criteria(config):
            await self._handle_alert_condition(config, alert_condition)
        
        # Check smart alerts (all types)
        if SMART_ALERTS_AVAILABLE and smart_alert_engine:
            try:
                current_data = {
                    'timestamp': energy_data.timestamp,
                    'solar_power': energy_data.solar_power,
                    'consumption': energy_data.consumption,
                    'battery_level': energy_data.battery_level,
                    'grid_consumption': energy_data.grid_consumption
                }
                
                smart_alerts = await smart_alert_engine.generate_all_smart_alerts(config, current_data)
                
                for smart_alert in smart_alerts:
                    if smart_alert.meets_criteria(config):
                        await self._handle_alert_condition(config, smart_alert)
                        
            except Exception as e:
                logger.error(f"Error processing smart alerts: {e}")
    
    async def _get_current_energy_data(self) -> Optional[EnergyData]:
        """Get current energy data from InfluxDB (placeholder)"""
        # This would integrate with your existing InfluxDB service
        # For now, return mock data
        try:
            # TODO: Integrate with actual InfluxDB service
            # For demo purposes, return simulated data
            import random
            current_time = datetime.now()
            
            # Simulate realistic energy data
            hour = current_time.hour
            if 6 <= hour <= 18:  # Daylight hours
                solar_power = max(0, 4.0 + random.uniform(-1.0, 2.0))
            else:
                solar_power = 0.0
            
            consumption = 2.0 + random.uniform(-0.5, 1.5)
            battery_level = 50 + random.uniform(-20, 30)
            battery_level = max(10, min(95, battery_level))
            
            return EnergyData(
                timestamp=current_time,
                solar_power=solar_power,
                consumption=consumption,
                battery_level=battery_level,
                grid_consumption=max(0, consumption - solar_power)
            )
        except Exception as e:
            logger.error(f"Error getting energy data: {e}")
            return None
    
    async def _evaluate_alert_conditions(self, config: AlertConfiguration, 
                                       energy_data: EnergyData, 
                                       daylight_info: DaylightInfo) -> Optional[AlertCondition]:
        """Evaluate all alert conditions"""
        try:
            # Current deficit
            current_deficit = self.deficit_detector.get_current_deficit(energy_data)
            
            # Sustained deficit check
            is_sustained, avg_deficit = self.deficit_detector.get_sustained_deficit(config, energy_data.timestamp)
            
            # Battery conditions
            battery_loss_detected, battery_loss = self.battery_monitor.get_battery_loss(config, energy_data.timestamp)
            is_battery_critical, critical_msg = self.battery_monitor.is_battery_critical(energy_data.battery_level, config)
            
            # Determine if conditions warrant an alert
            energy_deficit_significant = is_sustained and avg_deficit >= config.energy_thresholds.deficit_threshold_kw
            battery_condition_met = battery_loss_detected or is_battery_critical
            
            if energy_deficit_significant and battery_condition_met and daylight_info.is_daylight:
                # Calculate severity
                severity = self._calculate_severity(avg_deficit, energy_data.battery_level, battery_loss, config)
                
                return AlertCondition(
                    condition_id=f"deficit_{energy_data.timestamp.isoformat()}",
                    alert_type=AlertType.ENERGY_DEFICIT,
                    description=self._generate_alert_description(avg_deficit, energy_data.battery_level, battery_loss),
                    is_daylight=daylight_info.is_daylight,
                    energy_deficit=avg_deficit,
                    battery_level=energy_data.battery_level,
                    battery_loss=battery_loss,
                    weather_conditions={},  # Would be populated by weather intelligence
                    confidence=0.8,  # Base confidence, would be improved by ML
                    severity=severity,
                    timestamp=energy_data.timestamp
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error evaluating alert conditions: {e}")
            return None
    
    def _calculate_severity(self, deficit: float, battery_level: float, battery_loss: float, 
                          config: AlertConfiguration) -> AlertSeverity:
        """Calculate alert severity based on conditions"""
        score = 0
        
        # Deficit severity
        if deficit > config.energy_thresholds.deficit_threshold_kw * 2:
            score += 3
        elif deficit > config.energy_thresholds.deficit_threshold_kw:
            score += 2
        else:
            score += 1
        
        # Battery level severity
        if battery_level <= config.battery_thresholds.critical_level:
            score += 4
        elif battery_level <= config.battery_thresholds.min_level_threshold:
            score += 2
        else:
            score += 1
        
        # Battery loss severity
        if battery_loss > config.battery_thresholds.max_loss_threshold * 2:
            score += 3
        elif battery_loss > config.battery_thresholds.max_loss_threshold:
            score += 2
        
        # Map score to severity
        if score >= 8:
            return AlertSeverity.CRITICAL
        elif score >= 6:
            return AlertSeverity.HIGH
        elif score >= 4:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW
    
    def _generate_alert_description(self, deficit: float, battery_level: float, battery_loss: float) -> str:
        """Generate human-readable alert description"""
        description = f"Energy deficit of {deficit:.2f}kW detected during daylight hours. "
        description += f"Battery at {battery_level:.1f}%"
        
        if battery_loss > 0:
            description += f" (lost {battery_loss:.1f}% recently)"
        
        description += ". Immediate attention recommended."
        
        return description
    
    async def _handle_alert_condition(self, config: AlertConfiguration, condition: AlertCondition):
        """Handle detected alert condition"""
        # Check for existing similar alerts to prevent spam
        existing_alert = self._find_similar_active_alert(condition)
        
        if existing_alert:
            logger.info(f"Similar alert already active: {existing_alert.alert_id}")
            return
        
        # Create new alert instance
        alert_instance = AlertInstance(
            alert_id=f"{condition.alert_type.value}_{condition.timestamp.strftime('%Y%m%d_%H%M%S')}",
            user_id=config.user_id,
            alert_type=condition.alert_type,
            condition=condition,
            state=AlertState.ACTIVE
        )
        
        # Store alert
        self.active_alerts[alert_instance.alert_id] = alert_instance
        
        # Log alert creation
        logger.warning(f"ALERT TRIGGERED: {alert_instance.alert_id} - {condition.description}")
        
        # TODO: Integrate with existing AlertManager for notification delivery
        # This would call your existing notification system
        await self._send_alert_notification(alert_instance, config)
    
    def _find_similar_active_alert(self, condition: AlertCondition) -> Optional[AlertInstance]:
        """Find similar active alerts to prevent duplicates"""
        for alert in self.active_alerts.values():
            if (alert.alert_type == condition.alert_type and 
                alert.state == AlertState.ACTIVE and
                (datetime.utcnow() - alert.created_at).total_seconds() < 3600):  # Within last hour
                return alert
        return None
    
    async def _send_alert_notification(self, alert: AlertInstance, config: AlertConfiguration):
        """Send alert notification through configured channels"""
        # This would integrate with your existing AlertManager
        # For now, just log the alert
        logger.info(f"Alert notification would be sent: {alert.condition.description}")
        
        # TODO: Call existing AlertManager.create_alert() method
        # await alert_manager.create_alert(
        #     alert_type=alert.alert_type.value,
        #     severity=alert.condition.severity.value,
        #     message=alert.condition.description,
        #     channels=config.notification_channels
        # )
        
        alert.record_notification()