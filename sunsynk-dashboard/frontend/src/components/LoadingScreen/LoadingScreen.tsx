import React from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';

interface LoadingScreenProps {
  message?: string;
}

const LoadingScreen: React.FC<LoadingScreenProps> = ({ message = 'Loading...' }) => {
  return (
    <Box
      sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        background: 'linear-gradient(135deg, #2E8B57 0%, #52C878 100%)',
        zIndex: 9999,
      }}
    >
      <Box textAlign="center">
        <Typography
          variant="h3"
          component="h1"
          sx={{
            color: 'white',
            fontWeight: 600,
            mb: 2,
            fontSize: { xs: '2rem', md: '3rem' }
          }}
        >
          🌞 Sunsynk
        </Typography>
        
        <Typography
          variant="h6"
          component="h2"
          sx={{
            color: 'rgba(255, 255, 255, 0.9)',
            fontWeight: 400,
            mb: 4
          }}
        >
          Professional Energy Management
        </Typography>
        
        <CircularProgress
          size={60}
          thickness={4}
          sx={{
            color: 'white',
            mb: 3
          }}
        />
        
        <Typography
          variant="body1"
          sx={{
            color: 'rgba(255, 255, 255, 0.8)',
            fontSize: '1.1rem'
          }}
        >
          {message}
        </Typography>
      </Box>
    </Box>
  );
};

export default LoadingScreen;
