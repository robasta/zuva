#!/usr/bin/env python3
"""
Configuration Validation Script for Sunsynk Dashboard
Validates environment variables and data source configuration
"""

import os
import sys
from typing import List, Tuple

def load_env_file():
    """Load environment variables from .env file"""
    env_file = '.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

def check_required_env_vars() -> List[Tuple[str, bool, str]]:
    """Check required environment variables"""
    required_vars = [
        ('SUNSYNK_USERNAME', 'Sunsynk API username'),
        ('SUNSYNK_PASSWORD', 'Sunsynk API password'),
        ('OPENWEATHER_API_KEY', 'OpenWeather API key'),
        ('INFLUXDB_TOKEN', 'InfluxDB admin token'),
        ('JWT_SECRET_KEY', 'JWT secret key for authentication')
    ]
    
    optional_vars = [
        ('INFLUXDB_URL', 'InfluxDB URL', 'http://localhost:8086'),
        ('INFLUXDB_ORG', 'InfluxDB organization', 'sunsynk'),
        ('INFLUXDB_BUCKET', 'InfluxDB bucket', 'solar_metrics'),
        ('LOCATION', 'Weather location', 'Randburg,ZA'),
        ('USE_MOCK_DATA', 'Force mock data usage', 'false'),
        ('DISABLE_MOCK_FALLBACK', 'Disable mock data fallback', 'false')
    ]
    
    results = []
    
    print("🔍 Checking Required Environment Variables:")
    print("=" * 50)
    
    for var_name, description in required_vars:
        value = os.getenv(var_name)
        is_set = bool(value and value.strip())
        status = "✅ SET" if is_set else "❌ MISSING"
        print(f"{status} {var_name}: {description}")
        results.append((var_name, is_set, description))
    
    print("\n🔧 Optional Environment Variables:")
    print("=" * 50)
    
    for var_info in optional_vars:
        if len(var_info) == 3:
            var_name, description, default = var_info
            value = os.getenv(var_name, default)
            print(f"📝 {var_name}: {value} ({description})")
        else:
            var_name, description = var_info
            value = os.getenv(var_name, 'Not set')
            print(f"📝 {var_name}: {value} ({description})")
    
    return results

def check_data_source_config():
    """Check data source configuration"""
    print("\n📊 Data Source Configuration:")
    print("=" * 50)
    
    use_mock = os.getenv('USE_MOCK_DATA', 'false').lower() == 'true'
    disable_fallback = os.getenv('DISABLE_MOCK_FALLBACK', 'false').lower() == 'true'
    
    if use_mock:
        print("🎭 MODE: MOCK DATA ONLY")
        print("   - Application will use only synthetic data")
        print("   - Real API calls will be skipped")
    else:
        print("🌐 MODE: REAL DATA PREFERRED")
        if disable_fallback:
            print("   - No fallback to mock data")
            print("   - API will return errors if real data fails")
            print("   - ⚠️  STRICT MODE: Ensure all credentials are correct")
        else:
            print("   - Will fallback to mock data if real data fails")
            print("   - Provides resilient operation")

def validate_credentials():
    """Validate credential format"""
    print("\n🔐 Credential Validation:")
    print("=" * 50)
    
    username = os.getenv('SUNSYNK_USERNAME')
    password = os.getenv('SUNSYNK_PASSWORD')
    weather_key = os.getenv('OPENWEATHER_API_KEY')
    jwt_secret = os.getenv('JWT_SECRET_KEY')
    
    if username:
        if '@' in username:
            print("✅ SUNSYNK_USERNAME appears to be an email format")
        else:
            print("⚠️  SUNSYNK_USERNAME doesn't appear to be an email")
    
    if password:
        if len(password) >= 8:
            print("✅ SUNSYNK_PASSWORD has adequate length")
        else:
            print("⚠️  SUNSYNK_PASSWORD seems short (consider security)")
    
    if weather_key:
        if len(weather_key) == 32 and weather_key.isalnum():
            print("✅ OPENWEATHER_API_KEY format looks correct")
        else:
            print("⚠️  OPENWEATHER_API_KEY format may be incorrect")
    
    if jwt_secret:
        if len(jwt_secret) >= 32:
            print("✅ JWT_SECRET_KEY has adequate length")
        else:
            print("⚠️  JWT_SECRET_KEY should be longer for security")

def main():
    """Main validation function"""
    print("🌞 Sunsynk Dashboard Configuration Validator")
    print("=" * 60)
    
    # Load environment variables from .env file
    load_env_file()
    
    # Check if .env file exists
    env_file = '.env'
    if os.path.exists(env_file):
        print(f"✅ Found {env_file} file")
    else:
        print(f"⚠️  No {env_file} file found")
        print(f"   Copy .env.example to .env and configure your values")
    
    # Check required variables
    results = check_required_env_vars()
    
    # Check data source configuration
    check_data_source_config()
    
    # Validate credentials
    validate_credentials()
    
    # Summary
    print("\n📋 Summary:")
    print("=" * 50)
    
    missing_vars = [var for var, is_set, desc in results if not is_set]
    
    if missing_vars:
        print(f"❌ {len(missing_vars)} required variables missing:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n🚨 Application may not work correctly with missing variables")
        return 1
    else:
        print("✅ All required environment variables are set")
        
        use_mock = os.getenv('USE_MOCK_DATA', 'false').lower() == 'true'
        disable_fallback = os.getenv('DISABLE_MOCK_FALLBACK', 'false').lower() == 'true'
        
        if use_mock:
            print("🎭 Application configured for MOCK DATA mode")
        elif disable_fallback:
            print("🌐 Application configured for STRICT REAL DATA mode")
        else:
            print("🌐 Application configured for REAL DATA with fallback")
        
        print("\n🚀 Configuration appears ready for deployment!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
