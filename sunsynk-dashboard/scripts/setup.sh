#!/bin/bash

# Sunsynk Solar Dashboard Setup Script
# Automated setup for Raspberry Pi or Linux server deployment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check system requirements
check_requirements() {
    print_status "Checking system requirements..."
    
    # Check if running on supported OS
    if [[ "$OSTYPE" != "linux-gnu"* ]] && [[ "$OSTYPE" != "darwin"* ]]; then
        print_error "This script is designed for Linux or macOS. Current OS: $OSTYPE"
        exit 1
    fi
    
    # Check available memory (minimum 1GB)
    if command_exists free; then
        total_mem=$(free -m | awk 'NR==2{print $2}')
        if [ "$total_mem" -lt 1000 ]; then
            print_warning "Low memory detected: ${total_mem}MB. Minimum 1GB recommended."
        fi
    fi
    
    # Check available disk space (minimum 5GB)
    available_space=$(df . | awk 'NR==2{print $4}')
    if [ "$available_space" -lt 5000000 ]; then
        print_warning "Low disk space. Minimum 5GB recommended for the dashboard system."
    fi
    
    print_success "System requirements check completed"
}

# Function to install Docker
install_docker() {
    if command_exists docker; then
        print_status "Docker is already installed"
        docker --version
        return 0
    fi
    
    print_status "Installing Docker..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux installation
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        
        # Start and enable Docker service
        sudo systemctl start docker
        sudo systemctl enable docker
        
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS installation
        if command_exists brew; then
            brew install --cask docker
        else
            print_error "Please install Docker Desktop for Mac manually from https://docker.com"
            exit 1
        fi
    fi
    
    print_success "Docker installed successfully"
    print_warning "You may need to log out and back in for Docker permissions to take effect"
}

# Function to install Docker Compose
install_docker_compose() {
    if command_exists docker-compose; then
        print_status "Docker Compose is already installed"
        docker-compose --version
        return 0
    fi
    
    print_status "Installing Docker Compose..."
    
    # Get latest version
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep -Po '"tag_name": "\K[^"]*')
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # Usually comes with Docker Desktop on macOS
        if command_exists brew; then
            brew install docker-compose
        fi
    fi
    
    print_success "Docker Compose installed successfully"
}

# Function to setup environment file
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.template" ]; then
            cp .env.template .env
            print_status "Created .env file from template"
        else
            print_error ".env.template not found. Please ensure you're in the correct directory."
            exit 1
        fi
    else
        print_status ".env file already exists"
    fi
    
    print_warning "Please edit the .env file with your actual credentials:"
    print_warning "  - SUNSYNK_USERNAME and SUNSYNK_PASSWORD (required)"
    print_warning "  - WEATHER_API_KEY for weather integration (optional)"
    print_warning "  - Notification service credentials (optional)"
    
    # Ask if user wants to edit now
    read -p "Would you like to edit the .env file now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command_exists nano; then
            nano .env
        elif command_exists vim; then
            vim .env
        elif command_exists vi; then
            vi .env
        else
            print_warning "No text editor found. Please edit .env manually."
        fi
    fi
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    # Create directories that should exist but might not be in git
    mkdir -p logs
    mkdir -p data/influxdb
    mkdir -p data/grafana
    mkdir -p nginx/ssl
    mkdir -p grafana/provisioning/{datasources,dashboards}
    mkdir -p grafana/dashboards
    
    # Set appropriate permissions
    chmod 755 logs
    chmod 755 data/influxdb
    chmod 755 data/grafana
    
    print_success "Directories created successfully"
}

# Function to generate SSL certificates (self-signed for development)
generate_ssl_certificates() {
    print_status "Generating SSL certificates..."
    
    if [ ! -f "nginx/ssl/server.crt" ]; then
        # Generate self-signed certificate for development
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/server.key \
            -out nginx/ssl/server.crt \
            -subj "/C=ZA/ST=WesternCape/L=CapeTown/O=SunsynkDashboard/CN=localhost"
        
        print_success "Self-signed SSL certificate generated"
        print_warning "For production, replace with a proper SSL certificate"
    else
        print_status "SSL certificate already exists"
    fi
}

# Function to create nginx configuration
create_nginx_config() {
    print_status "Creating nginx configuration..."
    
    mkdir -p nginx
    
    cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream dashboard_api {
        server dashboard-api:8000;
    }
    
    upstream web_dashboard {
        server web-dashboard:80;
    }
    
    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name _;
        return 301 https://$server_name$request_uri;
    }
    
    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name _;
        
        ssl_certificate /etc/nginx/ssl/server.crt;
        ssl_certificate_key /etc/nginx/ssl/server.key;
        
        # Modern SSL configuration
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        
        # API routes
        location /api/ {
            proxy_pass http://dashboard_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # WebSocket route
        location /ws {
            proxy_pass http://dashboard_api;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Frontend routes
        location / {
            proxy_pass http://web_dashboard;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF
    
    print_success "Nginx configuration created"
}

# Function to pull Docker images
pull_docker_images() {
    print_status "Pulling required Docker images..."
    
    # Pull base images to avoid build-time downloads
    docker pull python:3.11-slim
    docker pull influxdb:2.0
    docker pull grafana/grafana:latest
    docker pull nginx:alpine
    
    print_success "Docker images pulled successfully"
}

# Function to setup systemd service (Linux only)
setup_systemd_service() {
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        print_status "Skipping systemd service setup (not on Linux)"
        return 0
    fi
    
    print_status "Setting up systemd service..."
    
    SERVICE_FILE="/etc/systemd/system/sunsynk-dashboard.service"
    CURRENT_DIR=$(pwd)
    
    sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=Sunsynk Solar Dashboard
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$CURRENT_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable sunsynk-dashboard
    
    print_success "Systemd service created and enabled"
    print_status "You can now use: sudo systemctl start/stop/restart sunsynk-dashboard"
}

# Function to run initial tests
run_initial_tests() {
    print_status "Running initial system tests..."
    
    # Test Docker
    if ! docker run --rm hello-world > /dev/null 2>&1; then
        print_error "Docker test failed. Please check Docker installation."
        exit 1
    fi
    
    # Test Docker Compose
    if ! docker-compose config > /dev/null 2>&1; then
        print_error "Docker Compose configuration test failed."
        exit 1
    fi
    
    # Test environment file
    if [ ! -f ".env" ]; then
        print_error ".env file not found. Please run setup again."
        exit 1
    fi
    
    print_success "Initial tests passed"
}

# Function to display next steps
show_next_steps() {
    print_success "Setup completed successfully!"
    echo
    print_status "Next steps:"
    echo "1. Edit .env file with your Sunsynk credentials and API keys"
    echo "2. Start the dashboard: docker-compose up -d"
    echo "3. Access the web dashboard: https://localhost (or your server IP)"
    echo "4. Access Grafana monitoring: http://localhost:3001 (admin/admin)"
    echo "5. View API documentation: https://localhost/api/docs"
    echo
    print_status "Useful commands:"
    echo "  - View logs: docker-compose logs -f"
    echo "  - Stop services: docker-compose down"
    echo "  - Update services: docker-compose pull && docker-compose up -d"
    echo "  - Check status: docker-compose ps"
    echo
    print_warning "For production deployment:"
    echo "  - Replace self-signed SSL certificate with proper certificate"
    echo "  - Configure firewall rules"
    echo "  - Set up regular backups"
    echo "  - Configure proper DNS"
}

# Main setup function
main() {
    echo "======================================================"
    echo "  Sunsynk Solar Dashboard Setup Script"
    echo "======================================================"
    echo
    
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        print_warning "Running as root is not recommended. Consider running as a regular user."
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Run setup steps
    check_requirements
    install_docker
    install_docker_compose
    create_directories
    setup_environment
    generate_ssl_certificates
    create_nginx_config
    pull_docker_images
    setup_systemd_service
    run_initial_tests
    show_next_steps
    
    print_success "Setup script completed successfully!"
}

# Run main function
main "$@"