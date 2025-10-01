#!/bin/bash

# Sunsynk Solar Dashboard - Production Deployment Script
# Complete production setup with monitoring, security, and backup services

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${PROJECT_DIR}/logs/deployment.log"
ENVIRONMENT="production"
DOMAIN="${DOMAIN:-localhost}"
EMAIL="${LETSENCRYPT_EMAIL:-admin@sunsynk.local}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
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

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. Some operations may require non-root privileges."
    fi
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check OS
    if [[ "$(uname -s)" != "Linux" ]]; then
        error_exit "This script is designed for Linux systems"
    fi
    
    # Check architecture (ARM for Raspberry Pi)
    ARCH=$(uname -m)
    case $ARCH in
        armv7l|aarch64|arm64)
            log_success "ARM architecture detected: $ARCH"
            ;;
        x86_64)
            log_warning "x86_64 architecture detected. This script is optimized for ARM/Raspberry Pi."
            ;;
        *)
            log_warning "Unknown architecture: $ARCH"
            ;;
    esac
    
    # Check available memory
    TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
    if [[ $TOTAL_MEM -lt 3900 ]]; then
        log_warning "Available memory: ${TOTAL_MEM}MB. Recommended: 4GB+"
    else
        log_success "Available memory: ${TOTAL_MEM}MB"
    fi
    
    # Check available disk space
    DISK_SPACE=$(df -BG / | awk 'NR==2{gsub(/G/,""); print $4}')
    if [[ $DISK_SPACE -lt 20 ]]; then
        log_warning "Available disk space: ${DISK_SPACE}GB. Recommended: 32GB+"
    else
        log_success "Available disk space: ${DISK_SPACE}GB"
    fi
}

# Install Docker and Docker Compose
install_docker() {
    log_info "Installing Docker and Docker Compose..."
    
    if command -v docker >/dev/null 2>&1; then
        log_success "Docker already installed"
        docker --version
    else
        log_info "Installing Docker..."
        curl -fsSL https://get.docker.com | sh
        
        # Add current user to docker group
        if [[ $EUID -ne 0 ]]; then
            sudo usermod -aG docker "$USER"
            log_warning "Please log out and log back in for Docker group changes to take effect"
        fi
    fi
    
    if command -v docker-compose >/dev/null 2>&1; then
        log_success "Docker Compose already installed"
        docker-compose --version
    else
        log_info "Installing Docker Compose..."
        if [[ "$ARCH" == "armv7l" ]]; then
            # For ARM v7 (Raspberry Pi 3)
            sudo pip3 install docker-compose
        else
            # For ARM64 and x86_64
            DOCKER_COMPOSE_VERSION="2.20.2"
            sudo curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            sudo chmod +x /usr/local/bin/docker-compose
        fi
    fi
    
    # Enable Docker service
    sudo systemctl enable docker
    sudo systemctl start docker
}

# Setup project directories and permissions
setup_directories() {
    log_info "Setting up project directories..."
    
    cd "$PROJECT_DIR"
    
    # Create required directories
    mkdir -p {\
        logs,\
        data/{influxdb,influxdb-config,grafana,prometheus,alertmanager},\
        backups/{influxdb,config,logs},\
        nginx/ssl,\
        monitoring/logrotate\
    }
    
    # Set proper permissions
    chmod 755 logs data backups
    chmod 700 nginx/ssl
    chmod 755 data/{influxdb,influxdb-config,grafana,prometheus,alertmanager}
    
    # Create log rotation configuration
    cat > monitoring/logrotate.conf << 'EOF'
/var/lib/docker/containers/*/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        docker kill --signal=USR1 $(docker ps -q) 2>/dev/null || true
    endscript
}
EOF
    
    log_success "Project directories created"
}

# Setup environment configuration
setup_environment() {
    log_info "Setting up environment configuration..."
    
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env.template" ]]; then
            cp .env.template .env
            log_info "Environment template copied to .env"
        else
            error_exit ".env.template not found"
        fi
    fi
    
    # Set production-specific environment variables
    {
        echo ""
        echo "# Production Deployment Configuration"
        echo "ENVIRONMENT=production"
        echo "DOMAIN=${DOMAIN}"
        echo "LETSENCRYPT_EMAIL=${EMAIL}"
        echo "DATA_DIR=${PROJECT_DIR}/data"
        echo "LOG_LEVEL=INFO"
        echo "BACKUP_RETENTION_DAYS=30"
        echo "BACKUP_SCHEDULE=0 2 * * *"
    } >> .env
    
    log_success "Environment configuration updated"
    
    # Prompt for required credentials if not set
    if ! grep -q "^SUNSYNK_USERNAME=" .env || grep -q "^SUNSYNK_USERNAME=$" .env; then
        log_warning "Please update .env file with your Sunsynk credentials"
        echo "Required variables:"
        echo "  - SUNSYNK_USERNAME"
        echo "  - SUNSYNK_PASSWORD"
        echo "  - WEATHER_API_KEY"
        echo "  - Email settings for notifications"
    fi
}

# Generate SSL certificates
setup_ssl() {
    log_info "Setting up SSL certificates..."
    
    export ENVIRONMENT="production"
    export DOMAIN="$DOMAIN"
    export LETSENCRYPT_EMAIL="$EMAIL"
    
    if [[ -x "nginx/generate-ssl.sh" ]]; then
        ./nginx/generate-ssl.sh generate
    else
        error_exit "SSL generation script not found or not executable"
    fi
}

# Pull Docker images
pull_images() {
    log_info "Pulling Docker images..."
    
    # Pull base images
    docker pull influxdb:2.7-alpine
    docker pull nginx:alpine
    docker pull grafana/grafana:latest
    docker pull prom/prometheus:latest
    docker pull prom/alertmanager:latest
    docker pull prom/node-exporter:latest
    docker pull grafana/loki:latest
    docker pull grafana/promtail:latest
    docker pull python:3.11-slim
    docker pull node:18-alpine
    
    log_success "Docker images pulled"
}

# Deploy services
deploy_services() {
    log_info "Deploying production services..."
    
    # Stop any existing services
    docker-compose down --remove-orphans 2>/dev/null || true
    
    # Build and start core services
    log_info "Starting core services..."
    docker-compose -f docker-compose.yml up -d influxdb
    
    # Wait for InfluxDB to be ready
    log_info "Waiting for InfluxDB to be ready..."
    timeout 120 bash -c 'until docker-compose exec influxdb influx ping; do sleep 5; done'
    
    # Start remaining services
    log_info "Starting application services..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 30
    
    # Check service health
    check_service_health
}

# Deploy monitoring stack
deploy_monitoring() {
    log_info "Deploying monitoring stack..."
    
    # Start monitoring services
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile monitoring up -d
    
    # Wait for monitoring services
    sleep 20
    
    log_success "Monitoring stack deployed"
}

# Check service health
check_service_health() {
    log_info "Checking service health..."
    
    local services=("influxdb" "dashboard-api" "web-dashboard")
    local failed_services=()
    
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up (healthy)\|Up"; then
            log_success "Service $service is running"
        else
            log_error "Service $service is not healthy"
            failed_services+=("$service")
        fi
    done
    
    if [[ ${#failed_services[@]} -gt 0 ]]; then
        log_error "Failed services: ${failed_services[*]}"
        log_info "Checking logs for failed services..."
        for service in "${failed_services[@]}"; do
            echo "--- Logs for $service ---"
            docker-compose logs --tail=20 "$service"
        done
        return 1
    fi
    
    # Test API endpoint
    if curl -f http://localhost:8000/api/health >/dev/null 2>&1; then
        log_success "API health check passed"
    else
        log_warning "API health check failed"
    fi
    
    # Test frontend
    if curl -f http://localhost:3000/ >/dev/null 2>&1; then
        log_success "Frontend health check passed"
    else
        log_warning "Frontend health check failed"
    fi
}

# Setup systemd service
setup_systemd() {
    log_info "Setting up systemd service..."
    
    sudo tee /etc/systemd/system/sunsynk-dashboard.service > /dev/null << EOF
[Unit]
Description=Sunsynk Solar Dashboard
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${PROJECT_DIR}
ExecStart=/usr/local/bin/docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
TimeoutStartSec=0
User=${USER}
Group=${USER}

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable sunsynk-dashboard
    
    log_success "Systemd service created and enabled"
}

# Setup firewall rules
setup_firewall() {
    log_info "Setting up firewall rules..."
    
    if command -v ufw >/dev/null 2>&1; then
        # Enable UFW
        sudo ufw --force enable
        
        # Allow SSH
        sudo ufw allow ssh
        
        # Allow HTTP and HTTPS
        sudo ufw allow 80/tcp
        sudo ufw allow 443/tcp
        
        # Allow Grafana (optional)
        sudo ufw allow 3001/tcp comment "Grafana"
        
        # Deny direct access to application ports
        sudo ufw deny 8000/tcp comment "Direct API access"
        sudo ufw deny 3000/tcp comment "Direct frontend access"
        sudo ufw deny 8086/tcp comment "Direct InfluxDB access"
        
        log_success "Firewall rules configured"
    else
        log_warning "UFW not available. Please configure firewall manually."
    fi
}

# Setup backup schedule
setup_backup_schedule() {
    log_info "Setting up backup schedule..."
    
    # The backup service is handled by Docker Compose
    # Just ensure the backup profile is enabled
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production up -d backup
    
    log_success "Backup service started"
}

# Generate deployment report
generate_report() {
    local report_file="${PROJECT_DIR}/deployment-report.txt"
    
    {
        echo "Sunsynk Solar Dashboard - Production Deployment Report"
        echo "Generated: $(date)"
        echo "========================================================"
        echo
        echo "System Information:"
        echo "- OS: $(uname -a)"
        echo "- Architecture: $(uname -m)"
        echo "- Memory: $(free -h | awk '/^Mem:/{print $2}')"
        echo "- Disk: $(df -h / | awk 'NR==2{print $4" available"}')"
        echo
        echo "Docker Information:"
        docker --version
        docker-compose --version
        echo
        echo "Service Status:"
        docker-compose ps
        echo
        echo "Network Configuration:"
        echo "- Domain: $DOMAIN"
        echo "- SSL: $(test -f nginx/ssl/server.crt && echo 'Configured' || echo 'Not configured')"
        echo
        echo "Access Information:"
        echo "- Web Dashboard: https://$DOMAIN (or https://$(hostname -I | awk '{print $1}'))"
        echo "- API Documentation: https://$DOMAIN/api/docs"
        echo "- Grafana: https://$DOMAIN:3001 (admin/admin)"
        echo "- Prometheus: http://$(hostname -I | awk '{print $1}'):9090"
        echo
        echo "Important Files:"
        echo "- Configuration: .env"
        echo "- Logs: logs/"
        echo "- Backups: backups/"
        echo "- SSL Certificates: nginx/ssl/"
        echo
        echo "Next Steps:"
        echo "1. Update .env with your Sunsynk credentials"
        echo "2. Configure domain DNS to point to this server"
        echo "3. Set up proper SSL certificates for production domain"
        echo "4. Configure notification settings"
        echo "5. Test backup and restore procedures"
    } > "$report_file"
    
    log_success "Deployment report generated: $report_file"
    cat "$report_file"
}

# Main deployment function
main() {
    log_info "========================================"
    log_info "Sunsynk Solar Dashboard Production Deployment"
    log_info "========================================"
    
    # Create log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Pre-flight checks
    check_root
    check_requirements
    
    # Core setup
    install_docker
    setup_directories
    setup_environment
    
    # Infrastructure setup
    setup_ssl
    pull_images
    
    # Deployment
    deploy_services
    deploy_monitoring
    
    # System integration
    setup_systemd
    setup_firewall
    setup_backup_schedule
    
    # Verification and reporting
    sleep 10
    check_service_health
    generate_report
    
    log_success "========================================"
    log_success "Production deployment completed successfully!"
    log_success "========================================"
    
    echo
    echo "🎉 Sunsynk Solar Dashboard is now running in production mode!"
    echo
    echo "Next steps:"
    echo "1. Update .env with your Sunsynk credentials"
    echo "2. Access the dashboard at: https://$DOMAIN"
    echo "3. Configure your domain DNS"
    echo "4. Set up proper SSL certificates for your domain"
    echo
    echo "Useful commands:"
    echo "  - View logs: docker-compose logs -f"
    echo "  - Stop services: docker-compose down"
    echo "  - Start services: sudo systemctl start sunsynk-dashboard"
    echo "  - Check status: docker-compose ps"
}

# Error handling
trap 'log_error "Deployment failed at line $LINENO"' ERR

# Execute main function
main "$@"