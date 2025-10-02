---
goal: Fix Alert Persistence & Add 24hr Time Series Graph to Main Dashboard
version: 1.0
date_created: 2025-01-02
last_updated: 2025-01-02
owner: Development Team
status: 'Planned'
tags: ['upgrade', 'feature', 'dashboard', 'alerts', 'persistence']
---

# Fix Alert Persistence & Add 24hr Time Series Graph Implementation Plan

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This plan addresses two critical issues: fixing alert persistence in the database and adding a comprehensive time series graph to the main dashboard showing consumption, generation, and state of charge data with navigation controls.

## 1. Requirements & Constraints

### Alert Persistence Requirements
- **REQ-001**: Alerts must be persisted in database storage instead of in-memory only
- **REQ-002**: Alert history must survive application restarts
- **REQ-003**: Alert state changes (acknowledge, resolve) must be persisted
- **REQ-004**: Database schema must support alert metadata and timestamps
- **REQ-005**: Must maintain backward compatibility with existing alert system

### Time Series Graph Requirements
- **REQ-006**: Display 24-hour time series data on main dashboard
- **REQ-007**: Show consumption, generation, and state of charge metrics
- **REQ-008**: Provide date navigation to view historical data
- **REQ-009**: Support zoom functionality for shorter time periods
- **REQ-010**: Real-time updates for current day data
- **REQ-011**: Responsive design for mobile and desktop

### Technical Constraints
- **CON-001**: Must use existing InfluxDB infrastructure
- **CON-002**: Must integrate with current FastAPI backend
- **CON-003**: Must use React with Material-UI components
- **CON-004**: Must maintain existing WebSocket connections
- **CON-005**: Must not break existing dashboard functionality

### Performance Requirements
- **PER-001**: Graph data loading under 2 seconds
- **PER-002**: Smooth zoom and pan interactions
- **PER-003**: Efficient database queries for historical data
- **PER-004**: Minimal impact on current dashboard performance

## 2. Implementation Steps

### Implementation Phase 1: Alert Database Persistence

- GOAL-001: Implement database-backed alert storage system

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Create alert database schema in InfluxDB with measurements for active alerts, alert history, and alert state changes | |  |
| TASK-002 | Extend DatabaseManager class with alert storage methods (write_alert, update_alert_status, get_alerts_history) | |  |
| TASK-003 | Modify AlertManager class to use database storage instead of in-memory lists for active_alerts and alert_history | |  |
| TASK-004 | Implement alert persistence methods (save_alert, load_alerts, acknowledge_alert_db, resolve_alert_db) | |  |
| TASK-005 | Create database initialization method to load existing alerts on application startup | |  |
| TASK-006 | Add alert cleanup service to remove old resolved alerts based on retention policy | |  |

### Implementation Phase 2: Time Series Graph Backend

- GOAL-002: Develop backend API endpoints for time series graph data

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-007 | Create /api/dashboard/timeseries endpoint with date range, resolution, and metrics parameters | |  |
| TASK-008 | Implement InfluxDB queries for consumption, generation, and battery SOC historical data | |  |
| TASK-009 | Add data aggregation logic for different time resolutions (5min, 15min, 1hr) based on zoom level | |  |
| TASK-010 | Implement data interpolation for missing data points to ensure smooth graph rendering | |  |
| TASK-011 | Add real-time data streaming for current day updates via WebSocket | |  |
| TASK-012 | Create data validation and error handling for malformed or missing historical data | |  |

### Implementation Phase 3: Time Series Graph Frontend

- GOAL-003: Build interactive time series graph component for main dashboard

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-013 | Create TimeSeriesGraph React component using Chart.js or Recharts library | |  |
| TASK-014 | Implement date picker component for navigating to previous dates | |  |
| TASK-015 | Add zoom controls for switching between 24hr, 12hr, 6hr, and 3hr views | |  |
| TASK-016 | Implement pan functionality for navigating within selected time range | |  |
| TASK-017 | Add real-time data updates via WebSocket integration | |  |
| TASK-018 | Create responsive design with mobile-optimized touch controls | |  |

### Implementation Phase 4: Dashboard Integration

- GOAL-004: Integrate time series graph into main dashboard layout

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-019 | Modify main Dashboard.tsx to include TimeSeriesGraph component in appropriate grid position | |  |
| TASK-020 | Implement loading states and error handling for graph data fetching | |  |
| TASK-021 | Add graph controls toolbar with date navigation, zoom, and refresh buttons | |  |
| TASK-022 | Create graph legend and metric tooltips for enhanced user experience | |  |
| TASK-023 | Implement graph data caching to reduce API calls during navigation | |  |
| TASK-024 | Add keyboard shortcuts for common graph operations (zoom, navigate) | |  |

### Implementation Phase 5: Testing & Validation

- GOAL-005: Comprehensive testing and performance validation

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-025 | Test alert persistence across application restarts and database reconnections | |  |
| TASK-026 | Validate time series graph performance with large historical datasets | |  |
| TASK-027 | Test graph responsiveness across different screen sizes and devices | |  |
| TASK-028 | Validate real-time updates and WebSocket integration | |  |
| TASK-029 | Performance testing for concurrent users and high data volume scenarios | |  |
| TASK-030 | User acceptance testing for graph navigation and zoom functionality | |  |

## 3. Alternatives

- **ALT-001**: Use SQLite instead of InfluxDB for alert persistence - Rejected due to existing InfluxDB infrastructure
- **ALT-002**: Use Plotly instead of Chart.js for graphs - Considered but Chart.js provides better performance for real-time updates
- **ALT-003**: Separate dashboard page for time series instead of main dashboard - Rejected as main dashboard is primary user interface
- **ALT-004**: Use Redis for alert caching - Considered but InfluxDB provides better time-series capabilities

## 4. Dependencies

- **DEP-001**: InfluxDB instance running and accessible
- **DEP-002**: Chart.js or Recharts library for React time series visualization
- **DEP-003**: Existing WebSocket infrastructure for real-time updates
- **DEP-004**: FastAPI backend with database connection
- **DEP-005**: Material-UI components for consistent styling

## 5. Files

- **FILE-001**: `/backend/collector/database.py` - Extend with alert storage methods
- **FILE-002**: `/backend/main.py` - Modify AlertManager class for database persistence
- **FILE-003**: `/backend/main.py` - Add new time series API endpoint
- **FILE-004**: `/frontend/src/components/TimeSeriesGraph/TimeSeriesGraph.tsx` - New graph component
- **FILE-005**: `/frontend/src/pages/Dashboard/Dashboard.tsx` - Integrate graph into main dashboard
- **FILE-006**: `/frontend/src/services/apiService.ts` - Add time series data fetching methods
- **FILE-007**: `/frontend/package.json` - Add charting library dependency

## 6. Testing

- **TEST-001**: Unit tests for alert database storage methods
- **TEST-002**: Integration tests for alert persistence across restarts
- **TEST-003**: API tests for time series data endpoints
- **TEST-004**: Component tests for TimeSeriesGraph functionality
- **TEST-005**: E2E tests for dashboard graph interaction
- **TEST-006**: Performance tests for large historical data queries
- **TEST-007**: Mobile responsiveness tests for graph controls

## 7. Risks & Assumptions

- **RISK-001**: Large historical datasets may cause performance issues - Mitigation: Implement data pagination and caching
- **RISK-002**: InfluxDB connection failures may cause data loss - Mitigation: Add connection retry logic and fallback storage
- **RISK-003**: Real-time updates may overwhelm browser performance - Mitigation: Implement update throttling and data sampling
- **ASSUMPTION-001**: InfluxDB contains sufficient historical data for meaningful graphs
- **ASSUMPTION-002**: Users primarily need 24-hour view with occasional historical analysis
- **ASSUMPTION-003**: Current WebSocket infrastructure can handle additional real-time graph updates

## 8. Related Specifications / Further Reading

- [Dashboard Architecture Documentation](../DASHBOARD_ARCHITECTURE.md)
- [InfluxDB Time Series Best Practices](https://docs.influxdata.com/influxdb/v2.0/write-data/best-practices/)
- [Chart.js Time Series Documentation](https://www.chartjs.org/docs/latest/charts/line.html)
- [Material-UI Data Visualization Guidelines](https://mui.com/components/data-grid/)
