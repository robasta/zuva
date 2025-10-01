/**
 * Utility functions for formatting power values
 */

export const formatPower = (value: number): string => {
  if (!value && value !== 0) return '0 W';
  
  const absoluteValue = Math.abs(value);
  
  // If value is less than 1 kW (1000 W), display in watts
  if (absoluteValue < 1) {
    const watts = absoluteValue * 1000;
    return `${watts.toFixed(0)} W`;
  }
  
  // For values 1 kW and above, display in kilowatts
  return `${absoluteValue.toFixed(2)} kW`;
};

export const formatPowerWithSign = (value: number): string => {
  if (!value && value !== 0) return '0 W';
  
  const absoluteValue = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  
  // If value is less than 1 kW (1000 W), display in watts
  if (absoluteValue < 1) {
    const watts = absoluteValue * 1000;
    return `${sign}${watts.toFixed(0)} W`;
  }
  
  // For values 1 kW and above, display in kilowatts
  return `${sign}${absoluteValue.toFixed(2)} kW`;
};

export const formatEnergy = (value: number): string => {
  if (!value && value !== 0) return '0 Wh';
  
  const absoluteValue = Math.abs(value);
  
  // If value is less than 1 kWh, display in watt-hours
  if (absoluteValue < 1) {
    const watthours = absoluteValue * 1000;
    return `${watthours.toFixed(0)} Wh`;
  }
  
  // For values 1 kWh and above, display in kilowatt-hours
  return `${absoluteValue.toFixed(2)} kWh`;
};
