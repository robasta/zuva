import React, { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import AppRouter from './routes/AppRouter';
import './App.css';

const App: React.FC = () => {
  const [darkMode, setDarkMode] = useState(false);

  // Load dark mode preference from localStorage on startup
  useEffect(() => {
    const savedSettings = localStorage.getItem('dashboard_settings');
    if (savedSettings) {
      try {
        const settings = JSON.parse(savedSettings);
        setDarkMode(settings.darkMode || false);
      } catch (error) {
        console.warn('Failed to parse dashboard settings:', error);
      }
    }

    // Listen for storage changes to sync across tabs
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'dashboard_settings' && e.newValue) {
        try {
          const settings = JSON.parse(e.newValue);
          setDarkMode(settings.darkMode || false);
        } catch (error) {
          console.warn('Failed to parse dashboard settings from storage event:', error);
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const theme = createTheme({
    palette: {
      mode: darkMode ? 'dark' : 'light',
      primary: {
        main: '#1976d2',
      },
      secondary: {
        main: '#dc004e',
      },
    },
  });

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppRouter />
    </ThemeProvider>
  );
};

export default App;
