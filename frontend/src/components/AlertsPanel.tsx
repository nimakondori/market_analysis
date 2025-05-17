import { Box, Typography, List, ListItem, Chip, IconButton, Collapse } from '@mui/material';
import ReactMarkdown from 'react-markdown';
import { Alert } from '../types';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import { useState } from 'react';
dayjs.extend(utc);
dayjs.extend(timezone);

interface Props {
  alerts: Alert[];
  onAlertHover: (timestamps: string[] | null) => void;
  onExpandChange: (expanded: boolean) => void;
}

const AlertsPanel = ({ alerts, onAlertHover, onExpandChange }: Props) => {
  const [isExpanded, setIsExpanded] = useState(true);

  const handleExpandChange = (expanded: boolean) => {
    setIsExpanded(expanded);
    onExpandChange(expanded);
  };

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
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
        <Typography variant="h6">
          Market Alerts
        </Typography>
        <IconButton 
          onClick={() => handleExpandChange(!isExpanded)}
          size="small"
          sx={{ color: 'text.secondary' }}
        >
          {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </IconButton>
      </Box>
      <Collapse in={isExpanded}>
        <List>
          {[...alerts]
            .sort((a, b) => 
              dayjs.tz(b.timestamp, 'YYYY-MM-DD HH:mm:ss', 'America/New_York')
                .valueOf() - 
              dayjs.tz(a.timestamp, 'YYYY-MM-DD HH:mm:ss', 'America/New_York')
                .valueOf()
            )
            .map((alert) => (
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
                onMouseEnter={() => onAlertHover(alert.times && alert.times.length > 0 ? alert.times : [alert.timestamp])}
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
      </Collapse>
    </Box>
  );
};

export default AlertsPanel; 