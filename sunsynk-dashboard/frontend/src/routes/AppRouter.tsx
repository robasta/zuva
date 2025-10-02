import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from '../components/Layout/Layout';
import Analytics from '../pages/Analytics/Analytics';
import AlertDashboard from '../components/AlertConfiguration/AlertDashboard';
import { Settings } from '../pages/Settings/Settings';
import { Typography, Box, Paper } from '@mui/material';

// Temporary Dashboard component - will be replaced with full content
const Dashboard: React.FC = () => {
  return (
    <Box>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h4" gutterBottom>
          🌞 Sunsynk Solar Dashboard
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Dashboard content is being migrated to the new navigation system.
          The original dashboard functionality will be restored in the next update.
        </Typography>
        <Typography variant="body2" sx={{ mt: 2 }}>
          ✅ Navigation system with alerts link is now active!
        </Typography>
      </Paper>
    </Box>
  );
};

export const AppRouter: React.FC = () => {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/alerts" element={<AlertDashboard />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </Router>
  );
};

export default AppRouter;
