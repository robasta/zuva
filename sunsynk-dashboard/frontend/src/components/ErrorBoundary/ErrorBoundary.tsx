import React, { Component, ReactNode } from 'react';
import { Box, Button, Typography, Paper, Container } from '@mui/material';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: any;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('Error Boundary caught an error:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  render() {
    if (this.state.hasError) {
      return (
        <Box
          sx={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#F8F9FA',
            padding: 2
          }}
        >
          <Container maxWidth="md">
            <Paper
              elevation={3}
              sx={{
                padding: 4,
                textAlign: 'center',
                borderRadius: 2
              }}
            >
              <Typography
                variant="h4"
                component="h1"
                gutterBottom
                sx={{ color: '#DC3545', fontWeight: 600 }}
              >
                ⚠️ Something went wrong
              </Typography>
              
              <Typography
                variant="body1"
                sx={{ color: '#6C757D', mb: 3 }}
              >
                We're sorry, but something unexpected happened. Our team has been notified.
              </Typography>
              
              {this.state.error && (
                <Box
                  sx={{
                    backgroundColor: '#F8F9FA',
                    border: '1px solid #DEE2E6',
                    borderRadius: 1,
                    padding: 2,
                    mb: 3,
                    textAlign: 'left',
                    fontFamily: 'monospace'
                  }}
                >
                  <Typography variant="body2" sx={{ color: '#DC3545' }}>
                    {this.state.error.toString()}
                  </Typography>
                </Box>
              )}
              
              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
                <Button
                  variant="contained"
                  color="primary"
                  onClick={this.handleReset}
                  sx={{ minWidth: 120 }}
                >
                  Try Again
                </Button>
                
                <Button
                  variant="outlined"
                  color="primary"
                  onClick={this.handleReload}
                  sx={{ minWidth: 120 }}
                >
                  Reload Page
                </Button>
              </Box>
              
              <Typography
                variant="body2"
                sx={{ color: '#6C757D', mt: 3 }}
              >
                If this problem persists, please contact support.
              </Typography>
            </Paper>
          </Container>
        </Box>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
