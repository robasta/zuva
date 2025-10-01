#!/bin/bash

# Sunsynk Solar Dashboard - Backup Service Entrypoint
# Manages scheduled backups using cron with proper logging

set -euo pipefail

# Configuration
BACKUP_SCHEDULE="${BACKUP_SCHEDULE:-0 2 * * *}"  # Default: Daily at 2 AM
BACKUP_SCRIPT="/app/backup.sh"
CRON_LOG="/app/backups/cron.log"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [ENTRYPOINT] $*"
}

# Initialize backup service
init_backup_service() {
    log "Initializing Sunsynk backup service..."
    
    # Create backup directory
    mkdir -p /app/backups
    
    # Set up log file
    touch "${CRON_LOG}"
    
    # Make backup script executable
    chmod +x "${BACKUP_SCRIPT}"
    
    log "Backup service initialized"
}

# Set up cron job
setup_cron() {
    log "Setting up cron schedule: ${BACKUP_SCHEDULE}"
    
    # Create cron job
    echo "${BACKUP_SCHEDULE} /app/backup.sh >> ${CRON_LOG} 2>&1" > /tmp/backup-cron
    
    # Install cron job
    crontab /tmp/backup-cron
    
    # Verify cron job
    if crontab -l | grep -q "backup.sh"; then
        log "Cron job installed successfully"
        crontab -l | while read line; do
            log "Cron job: $line"
        done
    else
        log "ERROR: Failed to install cron job"
        exit 1
    fi
}

# Health check function
health_check() {
    # Check if cron is running
    if ! pgrep crond > /dev/null; then
        log "WARNING: crond not running"
        return 1
    fi
    
    # Check if backup script exists and is executable
    if [[ ! -x "${BACKUP_SCRIPT}" ]]; then
        log "WARNING: backup script not executable"
        return 1
    fi
    
    # Check backup directory
    if [[ ! -d "/app/backups" ]]; then
        log "WARNING: backup directory missing"
        return 1
    fi
    
    return 0
}

# Run immediate backup if requested
run_immediate_backup() {
    log "Running immediate backup..."
    if "${BACKUP_SCRIPT}"; then
        log "Immediate backup completed successfully"
    else
        log "ERROR: Immediate backup failed"
        exit 1
    fi
}

# Monitor cron logs
monitor_logs() {
    log "Starting log monitoring..."
    
    # Follow cron log file
    tail -f "${CRON_LOG}" &
    local tail_pid=$!
    
    # Health check loop
    while true; do
        sleep 300  # Check every 5 minutes
        
        if ! health_check; then
            log "Health check failed, attempting recovery..."
            
            # Restart cron if needed
            if ! pgrep crond > /dev/null; then
                log "Restarting crond..."
                crond
            fi
        fi
    done
}

# Signal handlers
handle_sigterm() {
    log "Received SIGTERM, shutting down gracefully..."
    killall tail 2>/dev/null || true
    killall crond 2>/dev/null || true
    exit 0
}

handle_sigint() {
    log "Received SIGINT, shutting down gracefully..."
    killall tail 2>/dev/null || true
    killall crond 2>/dev/null || true
    exit 0
}

# Set up signal handlers
trap handle_sigterm TERM
trap handle_sigint INT

# Main function
main() {
    log "========================================"
    log "Sunsynk Backup Service Starting"
    log "========================================"
    log "Schedule: ${BACKUP_SCHEDULE}"
    log "Log Level: ${LOG_LEVEL}"
    log "Retention Days: ${RETENTION_DAYS:-30}"
    log "========================================"
    
    # Initialize service
    init_backup_service
    
    # Check for immediate backup request
    if [[ "${1:-}" == "--immediate" ]] || [[ "${RUN_IMMEDIATE:-false}" == "true" ]]; then
        run_immediate_backup
        if [[ "${1:-}" == "--immediate" ]]; then
            exit 0
        fi
    fi
    
    # Set up scheduled backups
    setup_cron
    
    # Start cron daemon
    log "Starting cron daemon..."
    crond -f &
    local crond_pid=$!
    
    # Wait a moment for cron to start
    sleep 2
    
    if pgrep crond > /dev/null; then
        log "Cron daemon started successfully (PID: $crond_pid)"
    else
        log "ERROR: Failed to start cron daemon"
        exit 1
    fi
    
    # Initial health check
    if health_check; then
        log "Initial health check passed"
    else
        log "WARNING: Initial health check failed"
    fi
    
    log "Backup service is ready and monitoring"
    
    # Start monitoring
    monitor_logs
}

# Execute main function with all arguments
main "$@"