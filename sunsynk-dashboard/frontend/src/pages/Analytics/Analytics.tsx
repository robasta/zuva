import React from 'react';
import { Typography, Box } from '@mui/material';

const Analytics: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" sx={{ fontWeight: 600, mb: 3 }}>
        Analytics
      </Typography>
      <Typography variant="body1">
        Advanced analytics and detailed reporting will be available here.
      </Typography>
    </Box>
  );
};

export default Analytics;
