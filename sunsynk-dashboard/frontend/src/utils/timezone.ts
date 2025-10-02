// Timezone utility functions for the Sunsynk Dashboard
// Handles timezone-aware date/time formatting based on weather location settings

export interface WeatherLocationConfig {
  location_type: 'city' | 'coordinates';
  city?: string;
  latitude?: number;
  longitude?: number;
}

/**
 * Determines the timezone based on weather location settings
 * @param weatherLocation - The weather location configuration
 * @returns The timezone string (e.g., 'Africa/Johannesburg')
 */
export const getTimezoneFromLocation = (weatherLocation?: WeatherLocationConfig): string => {
  if (!weatherLocation) {
    return 'Africa/Johannesburg'; // Default to GMT+2
  }

  // Determine timezone based on weather location
  if (weatherLocation.location_type === 'coordinates' && weatherLocation.latitude && weatherLocation.longitude) {
    // For South Africa coordinates (approximate)
    if (weatherLocation.latitude >= -35 && weatherLocation.latitude <= -22 && 
        weatherLocation.longitude >= 16 && weatherLocation.longitude <= 33) {
      return 'Africa/Johannesburg'; // GMT+2
    }
  } else if (weatherLocation.location_type === 'city' && weatherLocation.city) {
    // Map common cities to timezones
    const cityLower = weatherLocation.city.toLowerCase();
    if (cityLower.includes('cape town') || cityLower.includes('johannesburg') || 
        cityLower.includes('durban') || cityLower.includes('pretoria') || 
        cityLower.includes(',za')) {
      return 'Africa/Johannesburg'; // GMT+2
    }
  }
  
  // Default to South African timezone (GMT+2)
  return 'Africa/Johannesburg';
};

/**
 * Formats a date/time with timezone awareness
 * @param date - Date object or string to format
 * @param options - Intl.DateTimeFormatOptions for customization
 * @param weatherLocation - Weather location config to determine timezone
 * @returns Formatted date/time string
 */
export const formatDateTimeWithTimezone = (
  date: Date | string, 
  options: Intl.DateTimeFormatOptions = {},
  weatherLocation?: WeatherLocationConfig
): string => {
  const timezone = getTimezoneFromLocation(weatherLocation);
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  
  const defaultOptions: Intl.DateTimeFormatOptions = {
    timeZone: timezone,
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    ...options
  };
  
  try {
    return dateObj.toLocaleString('en-ZA', defaultOptions);
  } catch (error) {
    // Fallback to basic formatting if timezone is not supported
    return dateObj.toLocaleString('en-ZA');
  }
};

/**
 * Formats time only with timezone awareness
 * @param date - Date object or string to format
 * @param weatherLocation - Weather location config to determine timezone
 * @returns Formatted time string
 */
export const formatTimeWithTimezone = (
  date: Date | string,
  weatherLocation?: WeatherLocationConfig
): string => {
  return formatDateTimeWithTimezone(date, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }, weatherLocation);
};

/**
 * Formats date only with timezone awareness
 * @param date - Date object or string to format
 * @param weatherLocation - Weather location config to determine timezone
 * @returns Formatted date string
 */
export const formatDateWithTimezone = (
  date: Date | string,
  weatherLocation?: WeatherLocationConfig
): string => {
  return formatDateTimeWithTimezone(date, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  }, weatherLocation);
};

/**
 * Gets the current date/time in the appropriate timezone
 * @param weatherLocation - Weather location config to determine timezone
 * @returns Current date/time string
 */
export const getCurrentTimeInTimezone = (weatherLocation?: WeatherLocationConfig): string => {
  return formatTimeWithTimezone(new Date(), weatherLocation);
};

/**
 * Gets the current date in the appropriate timezone
 * @param weatherLocation - Weather location config to determine timezone
 * @returns Current date string
 */
export const getCurrentDateInTimezone = (weatherLocation?: WeatherLocationConfig): string => {
  return formatDateWithTimezone(new Date(), weatherLocation);
};