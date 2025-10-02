import React from 'react';
import { Box, Container } from '@mui/material';
import { Navigation } from '../Navigation/Navigation';

interface LayoutProps {
  children: React.ReactNode;
  title?: string;
}

export const Layout: React.FC<LayoutProps> = ({ children, title }) => {
  return (
    <Box sx={{ flexGrow: 1 }}>
      <Navigation title={title} />
      <Container maxWidth="xl" sx={{ mt: 3, mb: 3 }}>
        {children}
      </Container>
    </Box>
  );
};

export default Layout;
