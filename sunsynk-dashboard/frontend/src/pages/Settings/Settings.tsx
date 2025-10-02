import React from 'react';
import {
  Paper,
  Typography,
  Box,
  FormControlLabel,
  Switch,
  Divider,
  TextField,
  Button,
  Grid,
} from '@mui/material';

export const Settings: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>
      
      <Paper sx={{ p: 3, mt: 2 }}>
        <Typography variant="h6" gutterBottom>
          Dashboard Configuration
        </Typography>
        
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Refresh Interval (seconds)"
              type="number"
              defaultValue={30}
              helperText="How often to update dashboard data"
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Location"
              defaultValue="Johannesburg, South Africa"
              helperText="Location for weather and solar calculations"
            />
          </Grid>
        </Grid>
        
        <Divider sx={{ my: 3 }} />
        
        <Typography variant="h6" gutterBottom>
          Notifications
        </Typography>
        
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <FormControlLabel
            control={<Switch defaultChecked />}
            label="Enable intelligent alerts"
          />
          <FormControlLabel
            control={<Switch defaultChecked />}
            label="Weather-based notifications"
          />
          <FormControlLabel
            control={<Switch />}
            label="Email notifications"
          />
          <FormControlLabel
            control={<Switch />}
            label="SMS notifications"
          />
        </Box>
        
        <Divider sx={{ my: 3 }} />
        
        <Button variant="contained" color="primary">
          Save Settings
        </Button>
      </Paper>
    </Box>
  );
};

export default Settings;
