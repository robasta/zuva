"""
Alert System Data Models
Defines data structures for intelligent alert configuration and state management
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Dict, List, Optional, Union
import json

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertState(Enum):
    """Alert lifecycle states"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

class AlertType(Enum):
    """Types of intelligent alerts"""
    ENERGY_DEFICIT = "energy_deficit"
    BATTERY_CRITICAL = "battery_critical"
    WEATHER_WARNING = "weather_warning"
    PEAK_DEMAND = "peak_demand"
    BATTERY_OPTIMIZATION = "battery_optimization"
    GRID_EXPORT_OPPORTUNITY = "grid_export_opportunity"
    COST_OPTIMIZATION = "cost_optimization"
    MAINTENANCE_REMINDER = "maintenance_reminder"

@dataclass
class DaylightConfiguration:
    """Daylight calculation configuration"""
    latitude: float = -26.1367  # Randburg, ZA
    longitude: float = 27.9892
    timezone: str = "Africa/Johannesburg"
    daylight_buffer_minutes: int = 30  # Extra minutes before/after sunrise/sunset
    use_civil_twilight: bool = True  # Include twilight hours

@dataclass
class BatteryThresholds:
    """Battery monitoring thresholds"""
    min_level_threshold: float = 40.0  # % - Alert when battery drops below this
    max_loss_threshold: float = 10.0  # % - Alert when battery loses this much
    loss_timeframe_minutes: int = 60  # Time window for loss calculation
    critical_level: float = 20.0  # % - Critical battery level
    
@dataclass
class EnergyDeficitThresholds:
    """Energy deficit detection thresholds"""
    deficit_threshold_kw: float = 0.5  # kW - Minimum deficit to trigger alert
    sustained_deficit_minutes: int = 15  # Minutes deficit must persist
    prediction_horizon_hours: int = 2  # Hours ahead to predict deficits
    deficit_severity_multiplier: float = 2.0  # Multiplier for severe deficits

@dataclass
class AlertConfiguration:
    """Comprehensive alert configuration"""
    user_id: str
    alert_type: AlertType
    enabled: bool = True
    
    # Core thresholds
    battery_thresholds: BatteryThresholds = field(default_factory=BatteryThresholds)
    energy_thresholds: EnergyDeficitThresholds = field(default_factory=EnergyDeficitThresholds)
    daylight_config: DaylightConfiguration = field(default_factory=DaylightConfiguration)
    
    # Notification preferences
    notification_channels: List[str] = field(default_factory=lambda: ["email", "push"])
    severity_filter: AlertSeverity = AlertSeverity.MEDIUM
    max_alerts_per_hour: int = 5
    
    # Advanced settings
    weather_intelligence_enabled: bool = True
    machine_learning_enabled: bool = True
    predictive_alerts_enabled: bool = True
    auto_threshold_adjustment: bool = True
    
    # Seasonal adjustments
    seasonal_adjustment_enabled: bool = True
    summer_daylight_buffer: int = 45  # Extra minutes for summer
    winter_daylight_buffer: int = 15  # Reduced buffer for winter
    
    # Custom parameters
    custom_parameters: Dict[str, Union[str, int, float, bool]] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary"""
        return {
            'user_id': self.user_id,
            'alert_type': self.alert_type.value,
            'enabled': self.enabled,
            'battery_thresholds': {
                'min_level_threshold': self.battery_thresholds.min_level_threshold,
                'max_loss_threshold': self.battery_thresholds.max_loss_threshold,
                'loss_timeframe_minutes': self.battery_thresholds.loss_timeframe_minutes,
                'critical_level': self.battery_thresholds.critical_level
            },
            'energy_thresholds': {
                'deficit_threshold_kw': self.energy_thresholds.deficit_threshold_kw,
                'sustained_deficit_minutes': self.energy_thresholds.sustained_deficit_minutes,
                'prediction_horizon_hours': self.energy_thresholds.prediction_horizon_hours,
                'deficit_severity_multiplier': self.energy_thresholds.deficit_severity_multiplier
            },
            'daylight_config': {
                'latitude': self.daylight_config.latitude,
                'longitude': self.daylight_config.longitude,
                'timezone': self.daylight_config.timezone,
                'daylight_buffer_minutes': self.daylight_config.daylight_buffer_minutes,
                'use_civil_twilight': self.daylight_config.use_civil_twilight
            },
            'notification_channels': self.notification_channels,
            'severity_filter': self.severity_filter.value,
            'max_alerts_per_hour': self.max_alerts_per_hour,
            'weather_intelligence_enabled': self.weather_intelligence_enabled,
            'machine_learning_enabled': self.machine_learning_enabled,
            'predictive_alerts_enabled': self.predictive_alerts_enabled,
            'auto_threshold_adjustment': self.auto_threshold_adjustment,
            'seasonal_adjustment_enabled': self.seasonal_adjustment_enabled,
            'summer_daylight_buffer': self.summer_daylight_buffer,
            'winter_daylight_buffer': self.winter_daylight_buffer,
            'custom_parameters': self.custom_parameters,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AlertConfiguration':
        """Create configuration from dictionary"""
        battery_thresholds = BatteryThresholds(**data.get('battery_thresholds', {}))
        energy_thresholds = EnergyDeficitThresholds(**data.get('energy_thresholds', {}))
        daylight_config = DaylightConfiguration(**data.get('daylight_config', {}))
        
        return cls(
            user_id=data['user_id'],
            alert_type=AlertType(data['alert_type']),
            enabled=data.get('enabled', True),
            battery_thresholds=battery_thresholds,
            energy_thresholds=energy_thresholds,
            daylight_config=daylight_config,
            notification_channels=data.get('notification_channels', ["email", "push"]),
            severity_filter=AlertSeverity(data.get('severity_filter', 'medium')),
            max_alerts_per_hour=data.get('max_alerts_per_hour', 5),
            weather_intelligence_enabled=data.get('weather_intelligence_enabled', True),
            machine_learning_enabled=data.get('machine_learning_enabled', True),
            predictive_alerts_enabled=data.get('predictive_alerts_enabled', True),
            auto_threshold_adjustment=data.get('auto_threshold_adjustment', True),
            seasonal_adjustment_enabled=data.get('seasonal_adjustment_enabled', True),
            summer_daylight_buffer=data.get('summer_daylight_buffer', 45),
            winter_daylight_buffer=data.get('winter_daylight_buffer', 15),
            custom_parameters=data.get('custom_parameters', {}),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.utcnow().isoformat()))
        )

@dataclass
class AlertCondition:
    """Represents a specific alert condition"""
    condition_id: str
    alert_type: AlertType
    description: str
    is_daylight: bool
    energy_deficit: float  # kW
    battery_level: float  # %
    battery_loss: float  # %
    weather_conditions: Dict[str, Union[str, float]]
    confidence: float  # 0.0 to 1.0
    severity: AlertSeverity
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def meets_criteria(self, config: AlertConfiguration) -> bool:
        """Check if condition meets alert criteria"""
        # Daylight check
        if not self.is_daylight:
            return False
            
        # Energy deficit check
        if self.energy_deficit < config.energy_thresholds.deficit_threshold_kw:
            return False
            
        # Battery condition check (either low level OR significant loss)
        battery_low = self.battery_level < config.battery_thresholds.min_level_threshold
        battery_loss_significant = self.battery_loss > config.battery_thresholds.max_loss_threshold
        
        if not (battery_low or battery_loss_significant):
            return False
            
        return True

@dataclass 
class AlertInstance:
    """Represents an active alert instance"""
    alert_id: str
    user_id: str
    alert_type: AlertType
    condition: AlertCondition
    state: AlertState = AlertState.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    notification_count: int = 0
    last_notification_at: Optional[datetime] = None
    
    def acknowledge(self):
        """Acknowledge the alert"""
        self.state = AlertState.ACKNOWLEDGED
        self.acknowledged_at = datetime.utcnow()
    
    def resolve(self):
        """Resolve the alert"""
        self.state = AlertState.RESOLVED
        self.resolved_at = datetime.utcnow()
    
    def suppress(self):
        """Suppress the alert temporarily"""
        self.state = AlertState.SUPPRESSED
    
    def can_send_notification(self, max_per_hour: int = 5) -> bool:
        """Check if notification can be sent based on rate limiting"""
        if self.state != AlertState.ACTIVE:
            return False
            
        # Rate limiting check
        if self.last_notification_at:
            time_since_last = datetime.utcnow() - self.last_notification_at
            if time_since_last.total_seconds() < 3600 / max_per_hour:  # Spread notifications across hour
                return False
                
        return True
    
    def record_notification(self):
        """Record that a notification was sent"""
        self.notification_count += 1
        self.last_notification_at = datetime.utcnow()