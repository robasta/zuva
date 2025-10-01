import React from 'react';
import { Drawer, Typography, Box } from '@mui/material';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
  drawerWidth: number;
}

const Sidebar: React.FC<SidebarProps> = ({ open, onClose, drawerWidth }) => {
  return (
    <Drawer
      variant="persistent"
      open={open}
      onClose={onClose}
      sx={{
        width: drawerWidth,
        flexShrink: 0,
      }}
    >
      <Box sx={{ width: drawerWidth, p: 2 }}>
        <Typography variant="h6">Sidebar (Simplified)</Typography>
        <Typography variant="body2">Router functionality disabled</Typography>
      </Box>
    </Drawer>
  );
};

export default Sidebar;
