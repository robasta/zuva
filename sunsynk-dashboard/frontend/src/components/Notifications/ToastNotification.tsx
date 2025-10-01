import React, { useState, useEffect } from 'react';
import {
  Snackbar,
  Alert,
  AlertTitle,
  IconButton,
  Box,
  Typography
} from '@mui/material';
import {
  Close as CloseIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  CheckCircle as CheckCircleIcon
} from '@mui/icons-material';

interface ToastNotificationProps {
  open: boolean;
  severity: 'success' | 'info' | 'warning' | 'error';
  title: string;
  message: string;
  autoHideDuration?: number;
  onClose: () => void;
}

const ToastNotification: React.FC<ToastNotificationProps> = ({
  open,
  severity,
  title,
  message,
  autoHideDuration = 6000,
  onClose
}) => {
  const getSeverityIcon = () => {
    switch (severity) {
      case 'error':
        return <ErrorIcon />;
      case 'warning':
        return <WarningIcon />;
      case 'info':
        return <InfoIcon />;
      case 'success':
        return <CheckCircleIcon />;
      default:
        return <InfoIcon />;
    }
  };

  return (
    <Snackbar
      open={open}
      autoHideDuration={autoHideDuration}
      onClose={onClose}
      anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      sx={{ mt: 8 }} // Account for app bar
    >
      <Alert
        severity={severity}
        onClose={onClose}
        icon={getSeverityIcon()}
        sx={{
          minWidth: 300,
          maxWidth: 500,
          '& .MuiAlert-message': {
            width: '100%'
          }
        }}
      >
        <AlertTitle>{title}</AlertTitle>
        <Typography variant="body2">
          {message}
        </Typography>
      </Alert>
    </Snackbar>
  );
};

export default ToastNotification;
