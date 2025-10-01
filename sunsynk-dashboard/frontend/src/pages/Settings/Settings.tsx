import React from 'react';
import { Typography, Box } from '@mui/material';

const Settings: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" sx={{ fontWeight: 600, mb: 3 }}>
        Settings
      </Typography>
      <Typography variant="body1">
        System configuration and preferences will be available here.
      </Typography>
    </Box>
  );
};

export default Settings;
