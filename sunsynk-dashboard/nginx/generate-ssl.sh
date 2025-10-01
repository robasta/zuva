#!/bin/bash

# Sunsynk Solar Dashboard - SSL Certificate Generation Script
# Supports both self-signed (development) and Let's Encrypt (production) certificates

set -euo pipefail

# Configuration
SSL_DIR="/etc/nginx/ssl"
CERTBOT_DIR="/var/www/certbot"
DOMAIN="${DOMAIN:-localhost}"
EMAIL="${LETSENCRYPT_EMAIL:-admin@example.com}"
ENVIRONMENT="${ENVIRONMENT:-development}"

# Logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [SSL] $*"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

# Create SSL directory
setup_ssl_directory() {
    log "Setting up SSL directory..."
    mkdir -p "${SSL_DIR}"
    chmod 700 "${SSL_DIR}"
}

# Generate self-signed certificate for development
generate_selfsigned() {
    log "Generating self-signed SSL certificate for development..."
    
    # Generate private key
    openssl genrsa -out "${SSL_DIR}/server.key" 2048
    
    # Generate certificate
    openssl req -new -x509 -days 365 \
        -key "${SSL_DIR}/server.key" \
        -out "${SSL_DIR}/server.crt" \
        -subj "/C=ZA/ST=Western Cape/L=Cape Town/O=Sunsynk Solar Dashboard/OU=Development/CN=${DOMAIN}/emailAddress=dev@sunsynk.local"
    
    # Set proper permissions
    chmod 600 "${SSL_DIR}/server.key"
    chmod 644 "${SSL_DIR}/server.crt"
    
    log "Self-signed certificate generated successfully"
    log "Certificate: ${SSL_DIR}/server.crt"
    log "Private Key: ${SSL_DIR}/server.key"
    
    # Certificate information
    openssl x509 -in "${SSL_DIR}/server.crt" -text -noout | grep -E "Subject:|Not Before:|Not After:"
}

# Generate Let's Encrypt certificate for production
generate_letsencrypt() {
    log "Generating Let's Encrypt SSL certificate for production..."
    
    # Validate domain
    if [[ "${DOMAIN}" == "localhost" || "${DOMAIN}" == "*.local" ]]; then
        error_exit "Cannot use Let's Encrypt with localhost or .local domains. Use self-signed certificates instead."
    fi
    
    # Check if certbot is available
    if ! command -v certbot >/dev/null 2>&1; then
        log "Installing certbot..."
        if command -v apt-get >/dev/null 2>&1; then
            apt-get update
            apt-get install -y certbot
        elif command -v apk >/dev/null 2>&1; then
            apk add --no-cache certbot
        else
            error_exit "Cannot install certbot. Please install it manually."
        fi
    fi
    
    # Create webroot directory
    mkdir -p "${CERTBOT_DIR}"
    
    # Generate certificate using webroot method
    log "Requesting certificate for domain: ${DOMAIN}"
    certbot certonly \
        --webroot \
        --webroot-path="${CERTBOT_DIR}" \
        --email="${EMAIL}" \
        --agree-tos \
        --no-eff-email \
        --non-interactive \
        --domains="${DOMAIN}"
    
    # Copy certificates to nginx SSL directory
    cp "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" "${SSL_DIR}/server.crt"
    cp "/etc/letsencrypt/live/${DOMAIN}/privkey.pem" "${SSL_DIR}/server.key"
    
    # Set proper permissions
    chmod 600 "${SSL_DIR}/server.key"
    chmod 644 "${SSL_DIR}/server.crt"
    
    log "Let's Encrypt certificate generated successfully"
    log "Certificate: ${SSL_DIR}/server.crt"
    log "Private Key: ${SSL_DIR}/server.key"
}

# Renew Let's Encrypt certificate
renew_letsencrypt() {
    log "Renewing Let's Encrypt certificate..."
    
    if ! command -v certbot >/dev/null 2>&1; then
        error_exit "Certbot not found. Cannot renew certificate."
    fi
    
    # Attempt renewal
    if certbot renew --quiet; then
        log "Certificate renewed successfully"
        
        # Copy renewed certificates
        if [[ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]]; then
            cp "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" "${SSL_DIR}/server.crt"
            cp "/etc/letsencrypt/live/${DOMAIN}/privkey.pem" "${SSL_DIR}/server.key"
            
            # Set proper permissions
            chmod 600 "${SSL_DIR}/server.key"
            chmod 644 "${SSL_DIR}/server.crt"
            
            log "Certificates updated in nginx SSL directory"
            
            # Reload nginx if running
            if pgrep nginx >/dev/null; then
                nginx -s reload
                log "Nginx reloaded with new certificates"
            fi
        fi
    else
        log "Certificate renewal not needed or failed"
    fi
}

# Validate certificate
validate_certificate() {
    log "Validating SSL certificate..."
    
    if [[ ! -f "${SSL_DIR}/server.crt" ]] || [[ ! -f "${SSL_DIR}/server.key" ]]; then
        error_exit "SSL certificate files not found"
    fi
    
    # Check certificate validity
    if openssl x509 -in "${SSL_DIR}/server.crt" -checkend 86400 -noout; then
        log "Certificate is valid for at least 24 hours"
    else
        log "WARNING: Certificate expires within 24 hours"
    fi
    
    # Check private key
    if openssl rsa -in "${SSL_DIR}/server.key" -check -noout >/dev/null 2>&1; then
        log "Private key is valid"
    else
        error_exit "Private key is invalid"
    fi
    
    # Check if certificate and key match
    cert_hash=$(openssl x509 -in "${SSL_DIR}/server.crt" -pubkey -noout | openssl md5)
    key_hash=$(openssl rsa -in "${SSL_DIR}/server.key" -pubout 2>/dev/null | openssl md5)
    
    if [[ "$cert_hash" == "$key_hash" ]]; then
        log "Certificate and private key match"
    else
        error_exit "Certificate and private key do not match"
    fi
    
    log "SSL certificate validation completed successfully"
}

# Show certificate information
show_certificate_info() {
    if [[ -f "${SSL_DIR}/server.crt" ]]; then
        log "Certificate Information:"
        openssl x509 -in "${SSL_DIR}/server.crt" -text -noout | grep -E "Subject:|Issuer:|Not Before:|Not After:|DNS:|IP Address:"
    else
        log "No certificate found at ${SSL_DIR}/server.crt"
    fi
}

# Main function
main() {
    log "========================================"
    log "Sunsynk SSL Certificate Manager"
    log "========================================"
    log "Environment: ${ENVIRONMENT}"
    log "Domain: ${DOMAIN}"
    log "SSL Directory: ${SSL_DIR}"
    
    case "${1:-generate}" in
        "generate")
            setup_ssl_directory
            if [[ "${ENVIRONMENT}" == "production" && "${DOMAIN}" != "localhost" && "${DOMAIN}" != *".local" ]]; then
                generate_letsencrypt
            else
                generate_selfsigned
            fi
            validate_certificate
            show_certificate_info
            ;;
        "renew")
            if [[ "${ENVIRONMENT}" == "production" ]]; then
                renew_letsencrypt
            else
                log "Renewal not applicable for development environment"
            fi
            ;;
        "validate")
            validate_certificate
            show_certificate_info
            ;;
        "info")
            show_certificate_info
            ;;
        *)
            echo "Usage: $0 {generate|renew|validate|info}"
            echo "  generate - Generate new SSL certificate"
            echo "  renew    - Renew Let's Encrypt certificate (production only)"
            echo "  validate - Validate existing certificate"
            echo "  info     - Show certificate information"
            exit 1
            ;;
    esac
    
    log "SSL certificate operation completed"
}

# Execute main function
main "$@"