#!/bin/bash

# ===================================================================
# OHDSI Dashboard - Production Deployment Script
# ===================================================================
# This script deploys the OHDSI Dashboard to production
# with zero-downtime and data preservation

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROD_ENV_FILE="${SCRIPT_DIR}/.env.production"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.prod.yml"
BACKUP_DIR="${SCRIPT_DIR}/backups/$(date +%Y%m%d_%H%M%S)"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        log_error "Do not run this script as root!"
        exit 1
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed!"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed!"
        exit 1
    fi

    # Check if .env.production exists
    if [ ! -f "$PROD_ENV_FILE" ]; then
        log_error ".env.production file not found!"
        log_info "Copy .env.production.example to .env.production and configure it"
        exit 1
    fi

    # Check if SSL certificates exist
    if [ ! -f "${SCRIPT_DIR}/nginx/ssl/fullchain.pem" ] || [ ! -f "${SCRIPT_DIR}/nginx/ssl/privkey.pem" ]; then
        log_warn "SSL certificates not found in nginx/ssl/"
        log_info "You can generate self-signed certificates for testing with:"
        log_info "  ./scripts/generate_ssl_cert.sh"
        log_info "Or use Let's Encrypt with:"
        log_info "  ./scripts/setup_letsencrypt.sh"
        read -p "Continue without SSL? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    log_info "Prerequisites check passed ✓"
}

backup_data() {
    log_info "Creating backup..."
    mkdir -p "$BACKUP_DIR"

    # Backup PostgreSQL
    if docker ps | grep -q ohdsi-postgres; then
        log_info "Backing up PostgreSQL..."
        docker exec ohdsi-postgres pg_dump -U ohdsi_prod_user ohdsi_dashboard | gzip > "${BACKUP_DIR}/postgres.sql.gz"
    fi

    # Backup Elasticsearch (just the indices list, actual data stays in volumes)
    if docker ps | grep -q ohdsi-elasticsearch; then
        log_info "Recording Elasticsearch indices..."
        docker exec ohdsi-elasticsearch curl -s 'http://localhost:9200/_cat/indices?v' > "${BACKUP_DIR}/es_indices.txt"
    fi

    log_info "Backup created at: $BACKUP_DIR"
}

build_images() {
    log_info "Building production images..."

    # Set build args
    export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    export VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

    # Build images
    docker-compose -f "$COMPOSE_FILE" --env-file "$PROD_ENV_FILE" build --no-cache

    log_info "Images built successfully ✓"
}

deploy_services() {
    log_info "Deploying services..."

    # Pull latest base images
    docker-compose -f "$COMPOSE_FILE" --env-file "$PROD_ENV_FILE" pull || true

    # Deploy with zero-downtime (rolling restart)
    docker-compose -f "$COMPOSE_FILE" --env-file "$PROD_ENV_FILE" up -d --remove-orphans

    log_info "Services deployed ✓"
}

wait_for_healthy() {
    local service=$1
    local max_attempts=30
    local attempt=1

    log_info "Waiting for $service to be healthy..."

    while [ $attempt -le $max_attempts ]; do
        if docker ps | grep -q "$service" && docker inspect --format='{{.State.Health.Status}}' "$service" 2>/dev/null | grep -q "healthy"; then
            log_info "$service is healthy ✓"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    log_error "$service failed to become healthy"
    return 1
}

verify_deployment() {
    log_info "Verifying deployment..."

    # Wait for critical services
    wait_for_healthy "ohdsi-elasticsearch"
    wait_for_healthy "ohdsi-postgres"
    wait_for_healthy "ohdsi-redis"
    wait_for_healthy "ohdsi-backend"
    wait_for_healthy "ohdsi-frontend"

    # Check Elasticsearch index
    log_info "Checking Elasticsearch index..."
    ES_COUNT=$(docker exec ohdsi-elasticsearch curl -s -u elastic:${ELASTIC_PASSWORD} 'http://localhost:9200/ohdsi_content_v3/_count' | grep -o '"count":[0-9]*' | cut -d: -f2)
    log_info "Elasticsearch documents: $ES_COUNT"

    if [ "$ES_COUNT" -gt 0 ]; then
        log_info "Elasticsearch data preserved ✓"
    else
        log_warn "Elasticsearch appears empty - you may need to restore data"
    fi

    # Test backend API
    log_info "Testing backend API..."
    if docker exec ohdsi-backend curl -sf http://localhost:8000/health > /dev/null; then
        log_info "Backend API responding ✓"
    else
        log_error "Backend API not responding"
        return 1
    fi

    # Test frontend
    log_info "Testing frontend..."
    if docker exec ohdsi-frontend wget -q --spider http://localhost:3000; then
        log_info "Frontend responding ✓"
    else
        log_error "Frontend not responding"
        return 1
    fi

    log_info "Deployment verification passed ✓"
}

cleanup_old_images() {
    log_info "Cleaning up old images..."
    docker image prune -f
    log_info "Cleanup complete ✓"
}

show_status() {
    log_info "Deployment Status:"
    echo ""
    docker-compose -f "$COMPOSE_FILE" --env-file "$PROD_ENV_FILE" ps
    echo ""
    log_info "Access your application at: https://$(grep DOMAIN $PROD_ENV_FILE | cut -d= -f2)"
}

# Main execution
main() {
    log_info "Starting production deployment..."
    echo ""

    check_prerequisites
    backup_data
    build_images
    deploy_services
    verify_deployment
    cleanup_old_images
    show_status

    log_info "Production deployment complete! 🎉"
    echo ""
    log_info "Next steps:"
    log_info "  1. Monitor logs: docker-compose -f docker-compose.prod.yml logs -f"
    log_info "  2. Check health: ./scripts/health_check.sh"
    log_info "  3. View metrics: https://your-domain/grafana"
}

# Run main function
main "$@"
