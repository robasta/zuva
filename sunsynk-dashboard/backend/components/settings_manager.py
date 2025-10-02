"""
Persistent Settings Manager for Sunsynk Dashboard
Handles storage and retrieval of system settings, user preferences, and configurations
"""

import aiosqlite
import json
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class SettingItem:
    """Individual setting item"""
    key: str
    value: Any
    category: str
    user_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    description: Optional[str] = None

class SettingsManager:
    """Manages persistent storage of application settings"""
    
    def __init__(self, db_path: str = "/app/data/settings.db"):
        """Initialize settings manager with SQLite database"""
        self.db_path = db_path
        
        # Ensure directory exists with proper permissions
        db_dir = os.path.dirname(db_path)
        try:
            os.makedirs(db_dir, exist_ok=True)
            # Ensure the directory is writable
            if not os.access(db_dir, os.W_OK):
                logger.warning(f"Directory {db_dir} is not writable")
        except Exception as e:
            logger.error(f"Failed to create database directory {db_dir}: {e}")
        
        # Initialize database
        self._initialized = False
        logger.info(f"Settings manager initialized with database path: {self.db_path}")
    
    async def initialize(self):
        """Initialize database and create tables if they don't exist"""
        if self._initialized:
            return
            
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    user_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    description TEXT,
                    UNIQUE(key, user_id)
                )
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_settings_key_user 
                ON settings(key, user_id)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_settings_category 
                ON settings(category)
            """)
            
            await db.commit()
            
        self._initialized = True
        logger.info("Settings database initialized")
    
    async def set_setting(
        self, 
        key: str, 
        value: Any, 
        category: str = "general",
        user_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """Set a setting value"""
        await self.initialize()
        
        try:
            # Convert value to JSON string for storage
            value_str = json.dumps(value) if not isinstance(value, str) else value
            now = datetime.utcnow().isoformat()
            
            async with aiosqlite.connect(self.db_path) as db:
                # Try to update existing setting
                result = await db.execute("""
                    UPDATE settings 
                    SET value = ?, updated_at = ?, description = ?, category = ?
                    WHERE key = ? AND (user_id = ? OR (user_id IS NULL AND ? IS NULL))
                """, (value_str, now, description, category, key, user_id, user_id))
                
                if result.rowcount == 0:
                    # Insert new setting
                    await db.execute("""
                        INSERT INTO settings (key, value, category, user_id, created_at, updated_at, description)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (key, value_str, category, user_id, now, now, description))
                
                await db.commit()
                
            logger.info(f"Setting saved: {key} = {value} (category: {category}, user: {user_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            return False
    
    async def get_setting(
        self, 
        key: str, 
        user_id: Optional[str] = None, 
        default: Any = None
    ) -> Any:
        """Get a setting value"""
        await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute("""
                    SELECT value FROM settings 
                    WHERE key = ? AND (user_id = ? OR (user_id IS NULL AND ? IS NULL))
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (key, user_id, user_id))
                
                row = await cursor.fetchone()
                
                if row:
                    try:
                        # Try to parse as JSON, fall back to string
                        return json.loads(row['value'])
                    except (json.JSONDecodeError, TypeError):
                        return row['value']
                
                return default
                
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default
    
    async def get_settings_by_category(
        self, 
        category: str, 
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all settings in a category"""
        await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute("""
                    SELECT key, value FROM settings 
                    WHERE category = ? AND (user_id = ? OR (user_id IS NULL AND ? IS NULL))
                    ORDER BY key
                """, (category, user_id, user_id))
                
                rows = await cursor.fetchall()
                
                settings = {}
                for row in rows:
                    try:
                        settings[row['key']] = json.loads(row['value'])
                    except (json.JSONDecodeError, TypeError):
                        settings[row['key']] = row['value']
                
                return settings
                
        except Exception as e:
            logger.error(f"Error getting settings for category {category}: {e}")
            return {}
    
    async def get_user_settings(self, user_id: str) -> Dict[str, Any]:
        """Get all settings for a specific user"""
        await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute("""
                    SELECT key, value, category FROM settings 
                    WHERE user_id = ?
                    ORDER BY category, key
                """, (user_id,))
                
                rows = await cursor.fetchall()
                
                settings = {}
                for row in rows:
                    category = row['category']
                    if category not in settings:
                        settings[category] = {}
                    
                    try:
                        settings[category][row['key']] = json.loads(row['value'])
                    except (json.JSONDecodeError, TypeError):
                        settings[category][row['key']] = row['value']
                
                return settings
                
        except Exception as e:
            logger.error(f"Error getting user settings for {user_id}: {e}")
            return {}
    
    async def delete_setting(
        self, 
        key: str, 
        user_id: Optional[str] = None
    ) -> bool:
        """Delete a setting"""
        await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                result = await db.execute("""
                    DELETE FROM settings 
                    WHERE key = ? AND (user_id = ? OR (user_id IS NULL AND ? IS NULL))
                """, (key, user_id, user_id))
                
                await db.commit()
                
                if result.rowcount > 0:
                    logger.info(f"Setting deleted: {key} (user: {user_id})")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error deleting setting {key}: {e}")
            return False
    
    async def delete_user_settings(self, user_id: str) -> int:
        """Delete all settings for a user"""
        await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                result = await db.execute("""
                    DELETE FROM settings WHERE user_id = ?
                """, (user_id,))
                
                await db.commit()
                
                logger.info(f"Deleted {result.rowcount} settings for user {user_id}")
                return result.rowcount
                
        except Exception as e:
            logger.error(f"Error deleting user settings for {user_id}: {e}")
            return 0
    
    async def export_settings(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Export settings as JSON"""
        await self.initialize()
        
        export_data = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'settings': {}
        }
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                if user_id:
                    cursor = await db.execute("""
                        SELECT * FROM settings WHERE user_id = ?
                        ORDER BY category, key
                    """, (user_id,))
                else:
                    cursor = await db.execute("""
                        SELECT * FROM settings WHERE user_id IS NULL
                        ORDER BY category, key
                    """)
                
                rows = await cursor.fetchall()
                
                for row in rows:
                    category = row['category']
                    if category not in export_data['settings']:
                        export_data['settings'][category] = {}
                    
                    try:
                        value = json.loads(row['value'])
                    except (json.JSONDecodeError, TypeError):
                        value = row['value']
                    
                    export_data['settings'][category][row['key']] = {
                        'value': value,
                        'description': row['description'],
                        'updated_at': row['updated_at']
                    }
                
                return export_data
                
        except Exception as e:
            logger.error(f"Error exporting settings: {e}")
            return export_data
    
    async def import_settings(
        self, 
        import_data: Dict[str, Any], 
        user_id: Optional[str] = None,
        overwrite: bool = False
    ) -> int:
        """Import settings from JSON data"""
        await self.initialize()
        
        imported_count = 0
        
        if 'settings' not in import_data:
            logger.warning("No settings found in import data")
            return imported_count
        
        try:
            for category, settings in import_data['settings'].items():
                for key, setting_data in settings.items():
                    # Handle both old format (direct value) and new format (dict with value)
                    if isinstance(setting_data, dict) and 'value' in setting_data:
                        value = setting_data['value']
                        description = setting_data.get('description')
                    else:
                        value = setting_data
                        description = None
                    
                    # Check if setting exists if not overwriting
                    if not overwrite:
                        existing_value = await self.get_setting(key, user_id)
                        if existing_value is not None:
                            logger.info(f"Skipping existing setting: {key}")
                            continue
                    
                    # Import the setting
                    success = await self.set_setting(
                        key=key,
                        value=value,
                        category=category,
                        user_id=user_id,
                        description=description
                    )
                    
                    if success:
                        imported_count += 1
            
            logger.info(f"Imported {imported_count} settings")
            return imported_count
            
        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            return imported_count
    
    async def reset_to_defaults(self, user_id: Optional[str] = None):
        """Reset settings to default values"""
        await self.initialize()
        
        # Default settings
        defaults = {
            'dashboard': {
                'theme': 'light',
                'refresh_interval': 30,
                'auto_refresh': True,
                'show_advanced_metrics': False,
                'preferred_units': 'metric'
            },
            'alerts': {
                'email_enabled': True,
                'sms_enabled': False,
                'push_enabled': True,
                'quiet_hours_enabled': False,
                'quiet_start': '22:00',
                'quiet_end': '07:00',
                'severity_threshold': 'medium'
            },
            'battery': {
                'min_level_threshold': 30.0,
                'critical_level': 15.0,
                'max_loss_threshold': 10.0,
                'loss_timeframe_minutes': 60
            },
            'system': {
                'data_retention_days': 90,
                'backup_enabled': True,
                'maintenance_mode': False
            }
        }
        
        # Clear existing settings
        if user_id:
            await self.delete_user_settings(user_id)
        
        # Apply defaults
        count = 0
        for category, settings in defaults.items():
            for key, value in settings.items():
                success = await self.set_setting(
                    key=key,
                    value=value,
                    category=category,
                    user_id=user_id,
                    description=f"Default {category} setting"
                )
                if success:
                    count += 1
        
        logger.info(f"Reset {count} settings to defaults for user: {user_id}")
        return count

# Global settings manager instance
settings_manager = SettingsManager()