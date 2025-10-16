import React, { useState, useEffect } from 'react';
import { ThemeProvider, createTheme, alpha } from '@mui/material/styles';
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

  // Material-UI Dashboard Template Theme
  const theme = React.useMemo(() => {
    const defaultTheme = createTheme();
    
    // Brand colors from Material-UI template
    const brand = {
      50: 'hsl(210, 100%, 95%)',
      100: 'hsl(210, 100%, 92%)',
      200: 'hsl(210, 100%, 80%)',
      300: 'hsl(210, 100%, 65%)',
      400: 'hsl(210, 98%, 48%)',
      500: 'hsl(210, 98%, 42%)',
      600: 'hsl(210, 98%, 55%)',
      700: 'hsl(210, 98%, 35%)',
      800: 'hsl(210, 98%, 25%)',
      900: 'hsl(210, 98%, 15%)',
    };
    
    const gray = {
      50: 'hsl(220, 35%, 97%)',
      100: 'hsl(220, 30%, 94%)',
      200: 'hsl(220, 20%, 88%)',
      300: 'hsl(220, 20%, 80%)',
      400: 'hsl(220, 20%, 65%)',
      500: 'hsl(220, 20%, 42%)',
      600: 'hsl(220, 20%, 35%)',
      700: 'hsl(220, 20%, 25%)',
      800: 'hsl(220, 30%, 6%)',
      900: 'hsl(220, 35%, 3%)',
    };
    
    const green = {
      300: 'hsl(142, 76%, 73%)',
      400: 'hsl(142, 76%, 36%)',
      500: 'hsl(142, 76%, 30%)',
      600: 'hsl(142, 76%, 25%)',
      700: 'hsl(142, 76%, 20%)',
      800: 'hsl(142, 76%, 15%)',
    };
    
    return createTheme({
      typography: {
        fontFamily: 'Inter, sans-serif',
        h1: {
          fontSize: defaultTheme.typography.pxToRem(48),
          fontWeight: 600,
          lineHeight: 1.2,
          letterSpacing: -0.5,
        },
        h2: {
          fontSize: defaultTheme.typography.pxToRem(36),
          fontWeight: 600,
          lineHeight: 1.2,
        },
        h3: {
          fontSize: defaultTheme.typography.pxToRem(30),
          lineHeight: 1.2,
        },
        h4: {
          fontSize: defaultTheme.typography.pxToRem(24),
          fontWeight: 600,
          lineHeight: 1.5,
        },
        h5: {
          fontSize: defaultTheme.typography.pxToRem(20),
          fontWeight: 600,
        },
        h6: {
          fontSize: defaultTheme.typography.pxToRem(18),
          fontWeight: 600,
        },
        subtitle1: {
          fontSize: defaultTheme.typography.pxToRem(18),
        },
        subtitle2: {
          fontSize: defaultTheme.typography.pxToRem(14),
          fontWeight: 500,
        },
        body1: {
          fontSize: defaultTheme.typography.pxToRem(14),
        },
        body2: {
          fontSize: defaultTheme.typography.pxToRem(14),
          fontWeight: 400,
        },
        caption: {
          fontSize: defaultTheme.typography.pxToRem(12),
          fontWeight: 400,
        },
      },
      shape: {
        borderRadius: 8,
      },
      palette: {
        mode: darkMode ? 'dark' : 'light',
        primary: {
          light: brand[200],
          main: darkMode ? brand[400] : brand[500],
          dark: brand[700],
          contrastText: brand[50],
        },
        secondary: {
          main: '#dc004e',
        },
        success: {
          light: green[300],
          main: green[400],
          dark: green[800],
        },
        grey: gray,
        ...(darkMode
          ? {
              background: {
                default: gray[900],
                paper: 'hsl(220, 30%, 7%)',
              },
              text: {
                primary: 'hsl(0, 0%, 100%)',
                secondary: gray[400],
              },
              divider: alpha(gray[700], 0.6),
              action: {
                hover: alpha(gray[600], 0.2),
                selected: alpha(gray[600], 0.3),
              },
            }
          : {
              background: {
                default: 'hsl(0, 0%, 99%)',
                paper: 'hsl(220, 35%, 97%)',
              },
              text: {
                primary: gray[800],
                secondary: gray[600],
              },
              divider: alpha(gray[300], 0.4),
              action: {
                hover: alpha(gray[200], 0.2),
                selected: alpha(gray[200], 0.3),
              },
            }),
      },
    });
  }, [darkMode]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppRouter />
    </ThemeProvider>
  );
};

export default App;
