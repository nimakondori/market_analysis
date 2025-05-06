import { Box, Typography, List, ListItem, Chip } from '@mui/material';
import ReactMarkdown from 'react-markdown';
import { Alert } from '../types';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
dayjs.extend(utc);
dayjs.extend(timezone);

interface Props {
  alerts: Alert[];
  onAlertHover: (timestamp: string | null) => void;
}

const AlertsPanel = ({ alerts, onAlertHover }: Props) => {
  const getAlertColor = (type: Alert['type']) => {
    switch (type) {
      case 'buy':
        return 'success';
      case 'sell':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Market Alerts
      </Typography>
      <List>
        {alerts.map((alert) => (
          <ListItem
            key={alert.id}
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-start',
              mb: 2,
              p: 2,
              bgcolor: 'background.paper',
              borderRadius: 1,
              width: '100%',
              cursor: 'pointer',
              transition: 'background-color 0.2s',
              '&:hover': {
                bgcolor: 'action.hover',
              },
            }}
            onMouseEnter={() => onAlertHover(alert.timestamp)}
            onMouseLeave={() => onAlertHover(null)}
          >
            <Box display="flex" alignItems="center" gap={1} mb={1} width="100%">
              <Chip
                label={alert.type.toUpperCase()}
                color={getAlertColor(alert.type)}
                size="small"
              />
              <Chip
                label={`${Math.round(alert.confidence * 100)}% confidence`}
                variant="outlined"
                size="small"
              />
            </Box>
            <Box sx={{ width: '100%' }}>
              <ReactMarkdown>{alert.message.replace(/\*\*/g, '*')}</ReactMarkdown>
            </Box>
            <Typography variant="caption" color="text.secondary">
              {dayjs.tz(alert.timestamp, 'YYYY-MM-DD HH:mm:ss', 'America/New_York').format('YYYY-MM-DD HH:mm')} ET
            </Typography>
          </ListItem>
        ))}
      </List>
    </Box>
  );
};

export default AlertsPanel; 