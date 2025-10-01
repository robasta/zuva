import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  Container,
  Paper
} from '@mui/material';
import { useAuth } from '../../contexts/AuthContext';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const success = await login(username, password);
      if (!success) {
        setError('Invalid username or password');
      }
    } catch (err) {
      setError('Login failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #2E8B57 0%, #52C878 100%)',
        padding: 2
      }}
    >
      <Container maxWidth="sm">
        <Paper
          elevation={12}
          sx={{
            padding: 4,
            borderRadius: 3,
            background: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)'
          }}
        >
          <Box textAlign="center" mb={4}>
            <Typography variant="h3" component="h1" gutterBottom sx={{ color: '#2E8B57', fontWeight: 600 }}>
              🌞 Sunsynk
            </Typography>
            <Typography variant="h5" component="h2" gutterBottom sx={{ color: '#6C757D' }}>
              Solar Dashboard
            </Typography>
            <Typography variant="body1" sx={{ color: '#6C757D' }}>
              Professional Energy Management
            </Typography>
          </Box>

          <form onSubmit={handleSubmit}>
            <Box mb={3}>
              <TextField
                fullWidth
                label="Username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                disabled={isLoading}
                variant="outlined"
                sx={{
                  '& .MuiOutlinedInput-root': {
                    '&:hover fieldset': {
                      borderColor: '#2E8B57',
                    },
                    '&.Mui-focused fieldset': {
                      borderColor: '#2E8B57',
                    },
                  },
                }}
              />
            </Box>

            <Box mb={3}>
              <TextField
                fullWidth
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
                variant="outlined"
                sx={{
                  '& .MuiOutlinedInput-root': {
                    '&:hover fieldset': {
                      borderColor: '#2E8B57',
                    },
                    '&.Mui-focused fieldset': {
                      borderColor: '#2E8B57',
                    },
                  },
                }}
              />
            </Box>

            {error && (
              <Box mb={3}>
                <Alert severity="error">{error}</Alert>
              </Box>
            )}

            <Button
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              disabled={isLoading}
              sx={{
                py: 1.5,
                fontSize: '1.1rem',
                fontWeight: 600,
                backgroundColor: '#2E8B57',
                '&:hover': {
                  backgroundColor: '#1B5E3A',
                },
                '&:disabled': {
                  backgroundColor: '#6C757D',
                },
              }}
            >
              {isLoading ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                'Sign In'
              )}
            </Button>
          </form>

          <Box mt={4} textAlign="center">
            <Typography variant="body2" sx={{ color: '#6C757D' }}>
              Demo Credentials: admin / admin
            </Typography>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
};

export default Login;
