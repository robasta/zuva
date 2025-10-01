/**
 * Utility functions for data formatting and display
 */

// Format power values
export const formatPower = (value: number, unit: string = 'kW'): string => {
  if (isNaN(value)) return '0.0 ' + unit;
  
  if (Math.abs(value) >= 1000) {
    return (value / 1000).toFixed(1) + ' MW';
  } else if (Math.abs(value) >= 1) {
    return value.toFixed(2) + ' ' + unit;
  } else {
    return (value * 1000).toFixed(0) + ' W';
  }
};

// Format energy values
export const formatEnergy = (value: number, unit: string = 'kWh'): string => {
  if (isNaN(value)) return '0.0 ' + unit;
  
  if (Math.abs(value) >= 1000) {
    return (value / 1000).toFixed(1) + ' MWh';
  } else {
    return value.toFixed(2) + ' ' + unit;
  }
};

// Format percentage values
export const formatPercentage = (value: number, decimals: number = 1): string => {
  if (isNaN(value)) return '0%';
  return value.toFixed(decimals) + '%';
};

// Format voltage values
export const formatVoltage = (value: number): string => {
  if (isNaN(value)) return '0.0 V';
  return value.toFixed(1) + ' V';
};

// Format current values
export const formatCurrent = (value: number): string => {
  if (isNaN(value)) return '0.0 A';
  return value.toFixed(2) + ' A';
};

// Format time durations
export const formatDuration = (minutes: number): string => {
  if (isNaN(minutes) || minutes < 0) return 'N/A';
  
  const hours = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  
  if (hours > 24) {
    const days = Math.floor(hours / 24);
    const remainingHours = hours % 24;
    return `${days}d ${remainingHours}h`;
  } else if (hours > 0) {
    return `${hours}h ${mins}m`;
  } else {
    return `${mins}m`;
  }
};

// Format date/time
export const formatDateTime = (date: string | Date): string => {
  const d = new Date(date);
  if (isNaN(d.getTime())) return 'Invalid Date';
  
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// Format time only
export const formatTime = (date: string | Date): string => {
  const d = new Date(date);
  if (isNaN(d.getTime())) return 'Invalid Time';
  
  return d.toLocaleString('en-US', {
    hour: '2-digit',
    minute: '2-digit'
  });
};

// Format currency
export const formatCurrency = (value: number, currency: string = 'USD'): string => {
  if (isNaN(value)) return '$0.00';
  
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency
  }).format(value);
};

// Format large numbers
export const formatNumber = (value: number, decimals: number = 0): string => {
  if (isNaN(value)) return '0';
  
  if (Math.abs(value) >= 1000000) {
    return (value / 1000000).toFixed(decimals) + 'M';
  } else if (Math.abs(value) >= 1000) {
    return (value / 1000).toFixed(decimals) + 'K';
  } else {
    return value.toFixed(decimals);
  }
};

// Get status color based on value and thresholds
export const getStatusColor = (value: number, type: 'battery' | 'solar' | 'grid' | 'load'): string => {
  switch (type) {
    case 'battery':
      if (value >= 80) return '#28A745'; // Green
      if (value >= 50) return '#FFC107'; // Yellow
      if (value >= 20) return '#FF6B35'; // Orange
      return '#DC3545'; // Red
    
    case 'solar':
      if (value >= 4) return '#28A745'; // Green
      if (value >= 2) return '#FFC107'; // Yellow
      if (value >= 0.5) return '#FF6B35'; // Orange
      return '#DC3545'; // Red
    
    case 'grid':
      if (value <= 0) return '#28A745'; // Green (no grid usage)
      if (value <= 1) return '#FFC107'; // Yellow
      if (value <= 3) return '#FF6B35'; // Orange
      return '#DC3545'; // Red
    
    case 'load':
      if (value <= 2) return '#28A745'; // Green
      if (value <= 4) return '#FFC107'; // Yellow
      if (value <= 6) return '#FF6B35'; // Orange
      return '#DC3545'; // Red
    
    default:
      return '#6C757D'; // Gray
  }
};

// Get confidence color
export const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 0.8) return '#28A745'; // Green
  if (confidence >= 0.6) return '#FFC107'; // Yellow
  if (confidence >= 0.4) return '#FF6B35'; // Orange
  return '#DC3545'; // Red
};

// Get trend icon
export const getTrendIcon = (trend: string): string => {
  switch (trend.toLowerCase()) {
    case 'improving':
    case 'increasing':
    case 'up':
      return '📈';
    case 'deteriorating':
    case 'decreasing':
    case 'down':
      return '📉';
    case 'stable':
    case 'steady':
      return '➡️';
    default:
      return '❓';
  }
};

// Validate email
export const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

// Debounce function
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};

// Throttle function
export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle: boolean;
  
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};
