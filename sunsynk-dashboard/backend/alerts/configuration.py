"""
Alert Configuration Management System - Phase 2
Handles persistent storage and validation of alert configurations
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union
from dataclasses import asdict

from .models import AlertConfiguration, AlertType, AlertSeverity, BatteryThresholds, EnergyDeficitThresholds, DaylightConfiguration

logger = logging.getLogger(__name__)

class ConfigurationValidationError(Exception):
    """Exception raised for configuration validation errors"""
    pass

class ConfigurationManager:
    """Manages alert configuration storage, retrieval, and validation"""
    
    def __init__(self, storage_backend: str = "file"):
        """
        Initialize configuration manager
        
        Args:
            storage_backend: Storage type ('file', 'database', 'memory')
        """
        self.storage_backend = storage_backend
        self.configurations: Dict[str, AlertConfiguration] = {}
        
        # Use persistent storage path - create directory if it doesn't exist
        import os
        self.storage_directory = "/app/config/alerts"
        os.makedirs(self.storage_directory, exist_ok=True)
        self.storage_path = os.path.join(self.storage_directory, "alert_configurations.json")
        
        self._load_configurations()
    
    def _load_configurations(self):
        """Load configurations from storage"""
        if self.storage_backend == "file":
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    for user_id, config_data in data.items():
                        try:
                            config = AlertConfiguration.from_dict(config_data)
                            self.configurations[user_id] = config
                        except Exception as e:
                            logger.error(f"Error loading configuration for user {user_id}: {e}")
            except FileNotFoundError:
                logger.info("No existing configuration file found, starting fresh")
            except Exception as e:
                logger.error(f"Error loading configurations: {e}")
    
    def _save_configurations(self):
        """Save configurations to storage"""
        if self.storage_backend == "file":
            try:
                data = {}
                for user_id, config in self.configurations.items():
                    data[user_id] = config.to_dict()
                
                with open(self.storage_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                    
            except Exception as e:
                logger.error(f"Error saving configurations: {e}")
                raise
    
    def create_configuration(self, user_id: str, alert_type: AlertType, **kwargs) -> AlertConfiguration:
        """
        Create new alert configuration with validation
        
        Args:
            user_id: User identifier
            alert_type: Type of alert to configure
            **kwargs: Configuration parameters
            
        Returns:
            Created configuration
            
        Raises:
            ConfigurationValidationError: If configuration is invalid
        """
        try:
            # Create configuration with defaults
            config = AlertConfiguration(
                user_id=user_id,
                alert_type=alert_type,
                **kwargs
            )
            
            # Validate configuration
            self.validate_configuration(config)
            
            # Store configuration
            config_key = f"{user_id}_{alert_type.value}"
            self.configurations[config_key] = config
            self._save_configurations()
            
            logger.info(f"Created alert configuration for user {user_id}, type {alert_type.value}")
            return config
            
        except Exception as e:
            logger.error(f"Error creating configuration: {e}")
            raise ConfigurationValidationError(f"Failed to create configuration: {e}")
    
    def update_configuration(self, user_id: str, alert_type: AlertType, updates: Dict) -> AlertConfiguration:
        """
        Update existing alert configuration
        
        Args:
            user_id: User identifier
            alert_type: Type of alert to update
            updates: Dictionary of updates to apply
            
        Returns:
            Updated configuration
            
        Raises:
            ConfigurationValidationError: If updates are invalid
        """
        config_key = f"{user_id}_{alert_type.value}"
        
        if config_key not in self.configurations:
            raise ConfigurationValidationError(f"Configuration not found for user {user_id}, type {alert_type.value}")
        
        try:
            # Get current configuration
            config = self.configurations[config_key]
            
            # Apply updates
            config_dict = config.to_dict()
            self._apply_updates(config_dict, updates)
            
            # Create updated configuration
            updated_config = AlertConfiguration.from_dict(config_dict)
            updated_config.updated_at = datetime.utcnow()
            
            # Validate updated configuration
            self.validate_configuration(updated_config)
            
            # Store updated configuration
            self.configurations[config_key] = updated_config
            self._save_configurations()
            
            logger.info(f"Updated alert configuration for user {user_id}, type {alert_type.value}")
            return updated_config
            
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            raise ConfigurationValidationError(f"Failed to update configuration: {e}")
    
    def _apply_updates(self, config_dict: Dict, updates: Dict):
        """Apply nested updates to configuration dictionary"""
        for key, value in updates.items():
            if isinstance(value, dict) and key in config_dict and isinstance(config_dict[key], dict):
                # Recursive update for nested dictionaries
                self._apply_updates(config_dict[key], value)
            else:
                config_dict[key] = value
    
    def get_configuration(self, user_id: str, alert_type: AlertType) -> Optional[AlertConfiguration]:
        """
        Get alert configuration for user and type
        
        Args:
            user_id: User identifier
            alert_type: Type of alert
            
        Returns:
            Configuration if found, None otherwise
        """
        config_key = f"{user_id}_{alert_type.value}"
        return self.configurations.get(config_key)
    
    def get_user_configurations(self, user_id: str) -> List[AlertConfiguration]:
        """
        Get all configurations for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            List of user's configurations
        """
        return [config for key, config in self.configurations.items() 
                if key.startswith(f"{user_id}_")]
    
    def delete_configuration(self, user_id: str, alert_type: AlertType) -> bool:
        """
        Delete alert configuration
        
        Args:
            user_id: User identifier
            alert_type: Type of alert
            
        Returns:
            True if deleted, False if not found
        """
        config_key = f"{user_id}_{alert_type.value}"
        
        if config_key in self.configurations:
            del self.configurations[config_key]
            self._save_configurations()
            logger.info(f"Deleted alert configuration for user {user_id}, type {alert_type.value}")
            return True
        
        return False
    
    def validate_configuration(self, config: AlertConfiguration):
        """
        Validate alert configuration
        
        Args:
            config: Configuration to validate
            
        Raises:
            ConfigurationValidationError: If configuration is invalid
        """
        errors = []
        
        # Validate battery thresholds
        if config.battery_thresholds.min_level_threshold < 0 or config.battery_thresholds.min_level_threshold > 100:
            errors.append("Battery minimum level threshold must be between 0 and 100")
        
        if config.battery_thresholds.max_loss_threshold < 0 or config.battery_thresholds.max_loss_threshold > 100:
            errors.append("Battery maximum loss threshold must be between 0 and 100")
        
        if config.battery_thresholds.critical_level < 0 or config.battery_thresholds.critical_level > 100:
            errors.append("Battery critical level must be between 0 and 100")
        
        if config.battery_thresholds.critical_level > config.battery_thresholds.min_level_threshold:
            errors.append("Battery critical level must be less than or equal to minimum level threshold")
        
        if config.battery_thresholds.loss_timeframe_minutes < 1 or config.battery_thresholds.loss_timeframe_minutes > 1440:
            errors.append("Battery loss timeframe must be between 1 and 1440 minutes")
        
        # Validate energy thresholds
        if config.energy_thresholds.deficit_threshold_kw < 0:
            errors.append("Energy deficit threshold must be positive")
        
        if config.energy_thresholds.sustained_deficit_minutes < 1 or config.energy_thresholds.sustained_deficit_minutes > 240:
            errors.append("Sustained deficit minutes must be between 1 and 240")
        
        if config.energy_thresholds.prediction_horizon_hours < 1 or config.energy_thresholds.prediction_horizon_hours > 24:
            errors.append("Prediction horizon must be between 1 and 24 hours")
        
        # Validate daylight configuration
        if config.daylight_config.latitude < -90 or config.daylight_config.latitude > 90:
            errors.append("Latitude must be between -90 and 90 degrees")
        
        if config.daylight_config.longitude < -180 or config.daylight_config.longitude > 180:
            errors.append("Longitude must be between -180 and 180 degrees")
        
        if config.daylight_config.daylight_buffer_minutes < 0 or config.daylight_config.daylight_buffer_minutes > 120:
            errors.append("Daylight buffer must be between 0 and 120 minutes")
        
        # Validate notification settings
        if config.max_alerts_per_hour < 1 or config.max_alerts_per_hour > 60:
            errors.append("Maximum alerts per hour must be between 1 and 60")
        
        if not config.notification_channels:
            errors.append("At least one notification channel must be specified")
        
        valid_channels = ["email", "sms", "whatsapp", "push", "voice"]
        for channel in config.notification_channels:
            if channel not in valid_channels:
                errors.append(f"Invalid notification channel: {channel}")
        
        # Validate seasonal settings
        if config.summer_daylight_buffer < 0 or config.summer_daylight_buffer > 120:
            errors.append("Summer daylight buffer must be between 0 and 120 minutes")
        
        if config.winter_daylight_buffer < 0 or config.winter_daylight_buffer > 120:
            errors.append("Winter daylight buffer must be between 0 and 120 minutes")
        
        if errors:
            raise ConfigurationValidationError("; ".join(errors))
    
    def get_default_configuration(self, user_id: str, alert_type: AlertType) -> AlertConfiguration:
        """
        Get default configuration for alert type
        
        Args:
            user_id: User identifier
            alert_type: Type of alert
            
        Returns:
            Default configuration
        """
        # Default configurations based on alert type
        defaults = {
            AlertType.ENERGY_DEFICIT: {
                'battery_thresholds': BatteryThresholds(
                    min_level_threshold=40.0,
                    max_loss_threshold=10.0,
                    loss_timeframe_minutes=60,
                    critical_level=20.0
                ),
                'energy_thresholds': EnergyDeficitThresholds(
                    deficit_threshold_kw=0.5,
                    sustained_deficit_minutes=15,
                    prediction_horizon_hours=2,
                    deficit_severity_multiplier=2.0
                ),
                'notification_channels': ["email", "push"],
                'severity_filter': AlertSeverity.MEDIUM
            },
            AlertType.BATTERY_CRITICAL: {
                'battery_thresholds': BatteryThresholds(
                    min_level_threshold=30.0,
                    max_loss_threshold=15.0,
                    loss_timeframe_minutes=30,
                    critical_level=15.0
                ),
                'notification_channels': ["email", "sms", "push"],
                'severity_filter': AlertSeverity.HIGH
            },
            AlertType.WEATHER_WARNING: {
                'energy_thresholds': EnergyDeficitThresholds(
                    prediction_horizon_hours=6,
                    deficit_threshold_kw=1.0
                ),
                'notification_channels': ["email", "push"],
                'severity_filter': AlertSeverity.LOW
            }
        }
        
        # Get type-specific defaults
        type_defaults = defaults.get(alert_type, {})
        
        # Create configuration with defaults
        config = AlertConfiguration(
            user_id=user_id,
            alert_type=alert_type,
            **type_defaults
        )
        
        return config
    
    def export_configuration(self, user_id: str) -> Dict:
        """
        Export user's alert configurations
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary containing all user configurations
        """
        user_configs = self.get_user_configurations(user_id)
        
        export_data = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'configurations': [config.to_dict() for config in user_configs]
        }
        
        return export_data
    
    def import_configuration(self, user_id: str, import_data: Dict) -> List[AlertConfiguration]:
        """
        Import user's alert configurations
        
        Args:
            user_id: User identifier
            import_data: Configuration data to import
            
        Returns:
            List of imported configurations
            
        Raises:
            ConfigurationValidationError: If import data is invalid
        """
        if 'configurations' not in import_data:
            raise ConfigurationValidationError("Invalid import data: missing configurations")
        
        imported_configs = []
        
        for config_data in import_data['configurations']:
            try:
                # Update user ID to current user
                config_data['user_id'] = user_id
                config_data['created_at'] = datetime.utcnow().isoformat()
                config_data['updated_at'] = datetime.utcnow().isoformat()
                
                # Create and validate configuration
                config = AlertConfiguration.from_dict(config_data)
                self.validate_configuration(config)
                
                # Store configuration
                config_key = f"{user_id}_{config.alert_type.value}"
                self.configurations[config_key] = config
                imported_configs.append(config)
                
            except Exception as e:
                logger.error(f"Error importing configuration: {e}")
                # Continue with other configurations
        
        if imported_configs:
            self._save_configurations()
            logger.info(f"Imported {len(imported_configs)} configurations for user {user_id}")
        
        return imported_configs
    
    def reset_to_defaults(self, user_id: str) -> List[AlertConfiguration]:
        """
        Reset user's configurations to defaults
        
        Args:
            user_id: User identifier
            
        Returns:
            List of default configurations created
        """
        # Remove existing configurations
        keys_to_remove = [key for key in self.configurations.keys() 
                         if key.startswith(f"{user_id}_")]
        
        for key in keys_to_remove:
            del self.configurations[key]
        
        # Create default configurations for main alert types
        default_types = [AlertType.ENERGY_DEFICIT, AlertType.BATTERY_CRITICAL, AlertType.WEATHER_WARNING]
        default_configs = []
        
        for alert_type in default_types:
            config = self.get_default_configuration(user_id, alert_type)
            config_key = f"{user_id}_{alert_type.value}"
            self.configurations[config_key] = config
            default_configs.append(config)
        
        self._save_configurations()
        logger.info(f"Reset configurations to defaults for user {user_id}")
        
        return default_configs

# Global configuration manager instance
config_manager = ConfigurationManager()