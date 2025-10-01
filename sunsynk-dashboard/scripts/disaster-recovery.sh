#!/bin/bash

# Sunsynk Solar Dashboard - Disaster Recovery Script
# Comprehensive backup, restore, and failover procedures

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
RECOVERY_LOG="${PROJECT_DIR}/logs/disaster-recovery.log"
DATE_FORMAT="%Y%m%d_%H%M%S"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${RECOVERY_LOG}"
}

log_info() {
    log "${BLUE}[INFO]${NC} $*"
}

log_success() {
    log "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    log "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    log "${RED}[ERROR]${NC} $*"
}

error_exit() {
    log_error "$1"
    exit 1
}

# Create comprehensive system backup
create_full_backup() {
    local backup_name="full_system_backup_$(date +"${DATE_FORMAT}")"
    local backup_path="${BACKUP_DIR}/${backup_name}"
    
    log_info "Creating full system backup: ${backup_name}"
    
    mkdir -p "${backup_path}"
    
    # Backup InfluxDB data
    log_info "Backing up InfluxDB data..."
    if docker-compose exec -T influxdb influx backup /tmp/backup-influx; then
        docker cp $(docker-compose ps -q influxdb):/tmp/backup-influx "${backup_path}/influxdb"
        log_success "InfluxDB backup completed"
    else
        log_error "InfluxDB backup failed"
        return 1
    fi
    
    # Backup configuration files
    log_info "Backing up configuration..."
    tar -czf "${backup_path}/config.tar.gz" \
        --exclude='logs/*' \
        --exclude='data/*' \
        --exclude='backups/*' \
        --exclude='node_modules' \
        --exclude='.git' \
        -C "${PROJECT_DIR}" .
    
    # Backup Docker volumes
    log_info "Backing up Docker volumes..."
    mkdir -p "${backup_path}/volumes"
    
    # InfluxDB data volume
    if docker volume inspect sunsynk-dashboard_influxdb_data >/dev/null 2>&1; then
        docker run --rm \
            -v sunsynk-dashboard_influxdb_data:/source:ro \
            -v "${backup_path}/volumes:/backup" \
            alpine tar -czf /backup/influxdb_data.tar.gz -C /source .
    fi
    
    # Grafana data volume
    if docker volume inspect sunsynk-dashboard_grafana_data >/dev/null 2>&1; then
        docker run --rm \
            -v sunsynk-dashboard_grafana_data:/source:ro \
            -v "${backup_path}/volumes:/backup" \
            alpine tar -czf /backup/grafana_data.tar.gz -C /source .
    fi
    
    # Create manifest file
    {
        echo "Sunsynk Solar Dashboard - Full System Backup"
        echo "Created: $(date)"
        echo "Backup Name: ${backup_name}"
        echo "System: $(uname -a)"
        echo "Docker Version: $(docker --version)"
        echo "Compose Version: $(docker-compose --version)"
        echo ""
        echo "Contents:"
        echo "- InfluxDB data: influxdb/"
        echo "- Configuration: config.tar.gz"
        echo "- Docker volumes: volumes/"
        echo ""
        echo "Restore command:"
        echo "  ./disaster-recovery.sh restore ${backup_name}"
    } > "${backup_path}/manifest.txt"
    
    # Calculate backup size
    local backup_size=$(du -sh "${backup_path}" | cut -f1)
    log_success "Full backup completed: ${backup_path} (${backup_size})"
    
    return 0
}

# Restore system from backup
restore_from_backup() {
    local backup_name="$1"
    local backup_path="${BACKUP_DIR}/${backup_name}"
    
    if [[ ! -d "${backup_path}" ]]; then
        error_exit "Backup not found: ${backup_path}"
    fi
    
    log_info "Restoring system from backup: ${backup_name}"
    
    # Confirm restore operation
    echo "⚠️  WARNING: This will completely restore the system from backup."
    echo "   All current data will be replaced!"
    echo "   Backup: ${backup_name}"
    echo
    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        log_info "Restore operation cancelled"
        exit 0
    fi
    
    # Stop all services
    log_info "Stopping all services..."
    docker-compose down --volumes --remove-orphans || true
    
    # Restore configuration
    if [[ -f "${backup_path}/config.tar.gz" ]]; then
        log_info "Restoring configuration..."
        tar -xzf "${backup_path}/config.tar.gz" -C "${PROJECT_DIR}"
        log_success "Configuration restored"
    fi
    
    # Restore Docker volumes
    if [[ -d "${backup_path}/volumes" ]]; then
        log_info "Restoring Docker volumes..."
        
        # Remove existing volumes
        docker volume rm sunsynk-dashboard_influxdb_data 2>/dev/null || true
        docker volume rm sunsynk-dashboard_grafana_data 2>/dev/null || true
        
        # Recreate volumes
        docker volume create sunsynk-dashboard_influxdb_data
        docker volume create sunsynk-dashboard_grafana_data
        
        # Restore InfluxDB data
        if [[ -f "${backup_path}/volumes/influxdb_data.tar.gz" ]]; then
            docker run --rm \
                -v sunsynk-dashboard_influxdb_data:/target \
                -v "${backup_path}/volumes:/backup" \
                alpine tar -xzf /backup/influxdb_data.tar.gz -C /target
        fi
        
        # Restore Grafana data
        if [[ -f "${backup_path}/volumes/grafana_data.tar.gz" ]]; then
            docker run --rm \
                -v sunsynk-dashboard_grafana_data:/target \
                -v "${backup_path}/volumes:/backup" \
                alpine tar -xzf /backup/grafana_data.tar.gz -C /target
        fi
        
        log_success "Docker volumes restored"
    fi
    
    # Restore InfluxDB data
    if [[ -d "${backup_path}/influxdb" ]]; then
        log_info "Restoring InfluxDB data..."
        
        # Start only InfluxDB
        docker-compose up -d influxdb
        
        # Wait for InfluxDB to be ready
        timeout 60 bash -c 'until docker-compose exec influxdb influx ping; do sleep 5; done'
        
        # Copy backup to container and restore
        docker cp "${backup_path}/influxdb" $(docker-compose ps -q influxdb):/tmp/restore-influx
        docker-compose exec influxdb influx restore /tmp/restore-influx
        
        log_success "InfluxDB data restored"
    fi
    
    # Start all services
    log_info "Starting all services..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
    
    # Wait for services to be ready
    sleep 30
    
    # Verify restore
    verify_system_health
    
    log_success "System restore completed successfully"
}

# Verify system health after recovery
verify_system_health() {
    log_info "Verifying system health..."
    
    local health_checks=(
        "InfluxDB:http://localhost:8086/health"
        "API:http://localhost:8000/api/health"
        "Frontend:http://localhost:3000/"
    )
    
    for check in "${health_checks[@]}"; do
        local service=$(echo "$check" | cut -d: -f1)
        local url=$(echo "$check" | cut -d: -f2-)
        
        if curl -f "$url" >/dev/null 2>&1; then
            log_success "$service health check passed"
        else
            log_error "$service health check failed"
        fi
    done
    
    # Check Docker services
    local failed_services=$(docker-compose ps --services --filter "status=exited")
    if [[ -n "$failed_services" ]]; then
        log_error "Failed services: $failed_services"
        return 1
    else
        log_success "All Docker services are running"
    fi
}

# Create emergency recovery image
create_recovery_image() {
    log_info "Creating emergency recovery image..."
    
    local image_name="sunsynk-recovery-$(date +"${DATE_FORMAT}")"
    local image_path="${BACKUP_DIR}/${image_name}.tar"
    
    # Save all Docker images
    log_info "Saving Docker images..."
    docker images --format "table {{.Repository}}:{{.Tag}}" | grep -v REPOSITORY | while read image; do
        if [[ "$image" != "<none>:<none>" ]]; then
            docker save "$image" >> "${image_path}"
        fi
    done
    
    # Compress the image
    gzip "${image_path}"
    
    local image_size=$(du -sh "${image_path}.gz" | cut -f1)
    log_success "Recovery image created: ${image_path}.gz (${image_size})"
}

# Load recovery image
load_recovery_image() {
    local image_file="$1"
    
    if [[ ! -f "$image_file" ]]; then
        error_exit "Recovery image not found: $image_file"
    fi
    
    log_info "Loading recovery image: $image_file"
    
    if [[ "$image_file" == *.gz ]]; then
        gunzip -c "$image_file" | docker load
    else
        docker load < "$image_file"
    fi
    
    log_success "Recovery image loaded successfully"
}

# Failover to backup site (placeholder)
failover_to_backup() {
    log_info "Initiating failover to backup site..."
    
    # This would implement failover logic for a backup server
    # For example:
    # 1. Sync latest data to backup site
    # 2. Update DNS to point to backup site
    # 3. Start services on backup site
    
    log_warning "Failover functionality not yet implemented"
    log_info "Manual steps required:"
    echo "1. Ensure backup site has latest data"
    echo "2. Update DNS records to point to backup site"
    echo "3. Start services on backup site"
    echo "4. Update monitoring and alerting"
}

# List available backups
list_backups() {
    log_info "Available backups:"
    
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_warning "No backup directory found"
        return
    fi
    
    local count=0
    for backup in "$BACKUP_DIR"/full_system_backup_*; do
        if [[ -d "$backup" ]]; then
            local backup_name=$(basename "$backup")
            local backup_date=$(echo "$backup_name" | sed 's/full_system_backup_//' | sed 's/_/ /')
            local backup_size=$(du -sh "$backup" | cut -f1)
            
            echo "  📦 $backup_name"
            echo "     Date: $backup_date"
            echo "     Size: $backup_size"
            echo
            
            ((count++))
        fi
    done
    
    if [[ $count -eq 0 ]]; then
        log_warning "No backups found"
    else
        log_info "Total backups: $count"
    fi
}

# Clean old backups
clean_old_backups() {
    local retention_days="${1:-30}"
    
    log_info "Cleaning backups older than $retention_days days..."
    
    local deleted=0
    find "$BACKUP_DIR" -name "full_system_backup_*" -type d -mtime +"$retention_days" | while read backup; do
        log_info "Removing old backup: $(basename "$backup")"
        rm -rf "$backup"
        ((deleted++))
    done
    
    if [[ $deleted -gt 0 ]]; then
        log_success "Removed $deleted old backups"
    else
        log_info "No old backups to remove"
    fi
}

# Show usage
show_usage() {
    echo "Sunsynk Solar Dashboard - Disaster Recovery Tool"
    echo
    echo "Usage: $0 <command> [options]"
    echo
    echo "Commands:"
    echo "  backup                    Create full system backup"
    echo "  restore <backup_name>     Restore from backup"
    echo "  list                      List available backups"
    echo "  verify                    Verify system health"
    echo "  create-image              Create recovery Docker image"
    echo "  load-image <image_file>   Load recovery Docker image"
    echo "  failover                  Initiate failover (placeholder)"
    echo "  clean [days]              Clean old backups (default: 30 days)"
    echo
    echo "Examples:"
    echo "  $0 backup"
    echo "  $0 restore full_system_backup_20250101_120000"
    echo "  $0 clean 14"
}

# Main function
main() {
    # Create log directory
    mkdir -p "$(dirname "$RECOVERY_LOG")"
    
    case "${1:-}" in
        "backup")
            create_full_backup
            ;;
        "restore")
            if [[ -z "${2:-}" ]]; then
                error_exit "Backup name required for restore"
            fi
            restore_from_backup "$2"
            ;;
        "list")
            list_backups
            ;;
        "verify")
            verify_system_health
            ;;
        "create-image")
            create_recovery_image
            ;;
        "load-image")
            if [[ -z "${2:-}" ]]; then
                error_exit "Image file required"
            fi
            load_recovery_image "$2"
            ;;
        "failover")
            failover_to_backup
            ;;
        "clean")
            clean_old_backups "${2:-30}"
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

# Error handling
trap 'log_error "Disaster recovery operation failed at line $LINENO"' ERR

# Execute main function
main "$@"