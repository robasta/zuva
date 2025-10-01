#!/bin/bash

# Sunsynk Solar Dashboard - Automated Backup Script
# Creates compressed backups of InfluxDB data with retention management

set -euo pipefail

# Configuration from environment variables
BACKUP_DIR="/app/backups"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
INFLUXDB_URL="${INFLUXDB_URL:-http://influxdb:8086}"
INFLUXDB_TOKEN="${INFLUXDB_TOKEN}"
INFLUXDB_ORG="${INFLUXDB_ORG:-sunsynk}"
BACKUP_PREFIX="sunsynk-backup"
DATE_FORMAT="%Y%m%d_%H%M%S"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${BACKUP_DIR}/backup.log"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Health check for InfluxDB
check_influxdb() {
    log "Checking InfluxDB health..."
    if ! curl -s "${INFLUXDB_URL}/health" > /dev/null; then
        error_exit "InfluxDB is not accessible at ${INFLUXDB_URL}"
    fi
    log "InfluxDB is healthy"
}

# Create backup directory structure
setup_backup_dir() {
    mkdir -p "${BACKUP_DIR}/influxdb"
    mkdir -p "${BACKUP_DIR}/config"
    mkdir -p "${BACKUP_DIR}/logs"
    log "Backup directories created"
}

# Backup InfluxDB data
backup_influxdb() {
    local timestamp=$(date +"${DATE_FORMAT}")
    local backup_name="${BACKUP_PREFIX}_influxdb_${timestamp}"
    local backup_path="${BACKUP_DIR}/influxdb/${backup_name}"
    
    log "Starting InfluxDB backup: ${backup_name}"
    
    # Create backup using InfluxDB CLI
    if ! influx backup "${backup_path}" \
        --host "${INFLUXDB_URL}" \
        --token "${INFLUXDB_TOKEN}" \
        --org "${INFLUXDB_ORG}"; then
        error_exit "InfluxDB backup failed"
    fi
    
    # Compress the backup
    if tar -czf "${backup_path}.tar.gz" -C "${BACKUP_DIR}/influxdb" "${backup_name}"; then
        rm -rf "${backup_path}"
        log "InfluxDB backup compressed: ${backup_path}.tar.gz"
    else
        error_exit "Failed to compress backup"
    fi
    
    # Calculate backup size
    local size=$(du -h "${backup_path}.tar.gz" | cut -f1)
    log "Backup size: ${size}"
}

# Backup configuration files
backup_config() {
    local timestamp=$(date +"${DATE_FORMAT}")
    local config_backup="${BACKUP_DIR}/config/config_${timestamp}.tar.gz"
    
    log "Starting configuration backup"
    
    # Backup configuration directories
    if tar -czf "${config_backup}" \
        -C "/app" \
        config/ \
        monitoring/ \
        nginx/ \
        .env 2>/dev/null || true; then
        log "Configuration backup created: ${config_backup}"
    else
        log "WARNING: Configuration backup failed (some files may not exist)"
    fi
}

# Backup application logs
backup_logs() {
    local timestamp=$(date +"${DATE_FORMAT}")
    local logs_backup="${BACKUP_DIR}/logs/logs_${timestamp}.tar.gz"
    
    log "Starting logs backup"
    
    if [ -d "/app/logs" ] && [ "$(ls -A /app/logs 2>/dev/null)" ]; then
        if tar -czf "${logs_backup}" -C "/app" logs/; then
            log "Logs backup created: ${logs_backup}"
        else
            log "WARNING: Logs backup failed"
        fi
    else
        log "No logs directory or empty, skipping logs backup"
    fi
}

# Clean old backups based on retention policy
cleanup_old_backups() {
    log "Starting cleanup of backups older than ${RETENTION_DAYS} days"
    
    # Clean InfluxDB backups
    find "${BACKUP_DIR}/influxdb" -name "${BACKUP_PREFIX}_influxdb_*.tar.gz" -type f -mtime +"${RETENTION_DAYS}" -delete 2>/dev/null || true
    
    # Clean config backups
    find "${BACKUP_DIR}/config" -name "config_*.tar.gz" -type f -mtime +"${RETENTION_DAYS}" -delete 2>/dev/null || true
    
    # Clean log backups
    find "${BACKUP_DIR}/logs" -name "logs_*.tar.gz" -type f -mtime +"${RETENTION_DAYS}" -delete 2>/dev/null || true
    
    # Count remaining backups
    local influx_count=$(find "${BACKUP_DIR}/influxdb" -name "*.tar.gz" | wc -l)
    local config_count=$(find "${BACKUP_DIR}/config" -name "*.tar.gz" | wc -l)
    local logs_count=$(find "${BACKUP_DIR}/logs" -name "*.tar.gz" | wc -l)
    
    log "Cleanup completed. Remaining backups: InfluxDB=${influx_count}, Config=${config_count}, Logs=${logs_count}"
}

# Generate backup report
generate_report() {
    local timestamp=$(date +"${DATE_FORMAT}")
    local report_file="${BACKUP_DIR}/backup_report_${timestamp}.txt"
    
    {
        echo "Sunsynk Solar Dashboard Backup Report"
        echo "Generated: $(date)"
        echo "======================================"
        echo
        echo "Backup Statistics:"
        echo "- InfluxDB backups: $(find "${BACKUP_DIR}/influxdb" -name "*.tar.gz" | wc -l)"
        echo "- Config backups: $(find "${BACKUP_DIR}/config" -name "*.tar.gz" | wc -l)"
        echo "- Log backups: $(find "${BACKUP_DIR}/logs" -name "*.tar.gz" | wc -l)"
        echo
        echo "Total backup size: $(du -sh "${BACKUP_DIR}" | cut -f1)"
        echo
        echo "Recent backups:"
        find "${BACKUP_DIR}" -name "*.tar.gz" -type f -mtime -7 -exec ls -lh {} \; | sort
    } > "${report_file}"
    
    log "Backup report generated: ${report_file}"
}

# Send backup notification
send_notification() {
    local status="$1"
    local message="$2"
    
    # Send to dashboard API if available
    if curl -s "http://dashboard-api:8000/api/health" > /dev/null 2>&1; then
        curl -s -X POST "http://dashboard-api:8000/api/alerts/backup" \
            -H "Content-Type: application/json" \
            -d "{\"status\": \"${status}\", \"message\": \"${message}\", \"timestamp\": \"$(date -Iseconds)\"}" \
            > /dev/null 2>&1 || true
    fi
}

# Main backup function
run_backup() {
    local start_time=$(date +%s)
    
    log "========================================"
    log "Starting Sunsynk backup process"
    log "========================================"
    
    trap 'error_exit "Backup interrupted"' INT TERM
    
    # Setup and checks
    setup_backup_dir
    check_influxdb
    
    # Perform backups
    backup_influxdb
    backup_config
    backup_logs
    
    # Maintenance
    cleanup_old_backups
    generate_report
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log "Backup completed successfully in ${duration} seconds"
    log "========================================"
    
    send_notification "success" "Backup completed successfully in ${duration} seconds"
}

# Handle backup errors
handle_error() {
    local error_msg="$1"
    log "BACKUP FAILED: ${error_msg}"
    send_notification "error" "Backup failed: ${error_msg}"
    exit 1
}

# Set error trap
trap 'handle_error "Unexpected error occurred"' ERR

# Main execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Install InfluxDB CLI if not present
    if ! command -v influx >/dev/null 2>&1; then
        log "Installing InfluxDB CLI..."
        wget -q https://dl.influxdata.com/influxdb/releases/influxdb2-client-2.7.3-linux-amd64.tar.gz
        tar xf influxdb2-client-2.7.3-linux-amd64.tar.gz
        mv influx /usr/local/bin/
        rm influxdb2-client-2.7.3-linux-amd64.tar.gz
        log "InfluxDB CLI installed"
    fi
    
    run_backup
fi