#!/bin/bash

# OHDSI Community Intelligence Platform - Deployment Script
# Usage: ./deploy.sh [environment] [action]
# Environments: local, staging, production
# Actions: deploy, rollback, status, logs

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENVIRONMENT=${1:-local}
ACTION=${2:-deploy}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Load environment-specific configuration
if [ -f "${PROJECT_ROOT}/.env.${ENVIRONMENT}" ]; then
    export $(cat "${PROJECT_ROOT}/.env.${ENVIRONMENT}" | grep -v '^#' | xargs)
fi

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
    fi
    
    # Check environment file
    if [ ! -f "${PROJECT_ROOT}/.env.${ENVIRONMENT}" ] && [ "${ENVIRONMENT}" != "local" ]; then
        log_warning "Environment file .env.${ENVIRONMENT} not found, using defaults"
    fi
    
    log_info "Prerequisites check passed"
}

build_images() {
    log_info "Building Docker images for ${ENVIRONMENT}..."
    
    cd "${PROJECT_ROOT}"
    
    if [ "${ENVIRONMENT}" == "production" ]; then
        docker-compose -f docker-compose.prod.yml build --no-cache
    else
        docker-compose build
    fi
    
    log_info "Docker images built successfully"
}

deploy_local() {
    log_info "Deploying to local environment..."
    
    cd "${PROJECT_ROOT}"
    
    # Stop existing containers
    docker-compose down
    
    # Start services
    docker-compose up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 10
    
    # Initialize database
    docker-compose exec -T backend python scripts/setup_database.py
    docker-compose exec -T backend python scripts/init_users.py
    
    # Load sample data (optional)
    if [ "${LOAD_SAMPLE_DATA:-true}" == "true" ]; then
        log_info "Loading sample data..."
        docker-compose exec -T backend python scripts/sample_data_generator.py
    fi
    
    log_info "Local deployment completed successfully"
    log_info "Access the application at http://localhost:3000"
}

deploy_staging() {
    log_info "Deploying to staging environment..."
    
    # Build and tag images
    build_images
    
    # Push to registry
    if [ -n "${DOCKER_REGISTRY}" ]; then
        log_info "Pushing images to registry ${DOCKER_REGISTRY}..."
        
        docker tag ohdsi-backend:latest ${DOCKER_REGISTRY}/ohdsi-backend:staging-${TIMESTAMP}
        docker tag ohdsi-frontend:latest ${DOCKER_REGISTRY}/ohdsi-frontend:staging-${TIMESTAMP}
        
        docker push ${DOCKER_REGISTRY}/ohdsi-backend:staging-${TIMESTAMP}
        docker push ${DOCKER_REGISTRY}/ohdsi-frontend:staging-${TIMESTAMP}
    fi
    
    # Deploy to staging server
    if [ -n "${STAGING_HOST}" ]; then
        log_info "Deploying to staging server ${STAGING_HOST}..."
        
        # Copy docker-compose file
        scp docker-compose.prod.yml ${STAGING_USER}@${STAGING_HOST}:/opt/ohdsi/
        
        # SSH and deploy
        ssh ${STAGING_USER}@${STAGING_HOST} << EOF
            cd /opt/ohdsi
            export IMAGE_TAG=staging-${TIMESTAMP}
            docker-compose -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.prod.yml up -d
            docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
EOF
    fi
    
    log_info "Staging deployment completed successfully"
}

deploy_production() {
    log_info "Deploying to production environment..."
    
    # Confirmation prompt
    read -p "Are you sure you want to deploy to PRODUCTION? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_warning "Production deployment cancelled"
        exit 0
    fi
    
    # Create backup
    log_info "Creating database backup..."
    if [ -n "${PRODUCTION_HOST}" ]; then
        ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} << EOF
            pg_dump -h localhost -U ${POSTGRES_USER} ${POSTGRES_DB} > /backups/ohdsi_backup_${TIMESTAMP}.sql
EOF
    fi
    
    # Build and tag images
    build_images
    
    # Push to registry
    if [ -n "${DOCKER_REGISTRY}" ]; then
        log_info "Pushing images to registry ${DOCKER_REGISTRY}..."
        
        docker tag ohdsi-backend:latest ${DOCKER_REGISTRY}/ohdsi-backend:production-${TIMESTAMP}
        docker tag ohdsi-frontend:latest ${DOCKER_REGISTRY}/ohdsi-frontend:production-${TIMESTAMP}
        
        docker push ${DOCKER_REGISTRY}/ohdsi-backend:production-${TIMESTAMP}
        docker push ${DOCKER_REGISTRY}/ohdsi-frontend:production-${TIMESTAMP}
        
        # Also tag as latest
        docker tag ${DOCKER_REGISTRY}/ohdsi-backend:production-${TIMESTAMP} ${DOCKER_REGISTRY}/ohdsi-backend:latest
        docker tag ${DOCKER_REGISTRY}/ohdsi-frontend:production-${TIMESTAMP} ${DOCKER_REGISTRY}/ohdsi-frontend:latest
        
        docker push ${DOCKER_REGISTRY}/ohdsi-backend:latest
        docker push ${DOCKER_REGISTRY}/ohdsi-frontend:latest
    fi
    
    # Deploy to production server
    if [ -n "${PRODUCTION_HOST}" ]; then
        log_info "Deploying to production server ${PRODUCTION_HOST}..."
        
        # Copy docker-compose file
        scp docker-compose.prod.yml ${PRODUCTION_USER}@${PRODUCTION_HOST}:/opt/ohdsi/
        
        # SSH and deploy with zero-downtime
        ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} << EOF
            cd /opt/ohdsi
            export IMAGE_TAG=production-${TIMESTAMP}
            
            # Pull new images
            docker-compose -f docker-compose.prod.yml pull
            
            # Start new containers alongside old ones
            docker-compose -f docker-compose.prod.yml up -d --scale backend=2 --scale frontend=2
            
            # Wait for new containers to be healthy
            sleep 30
            
            # Run migrations
            docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
            
            # Stop old containers
            docker-compose -f docker-compose.prod.yml up -d --scale backend=1 --scale frontend=1
            
            # Clean up old containers
            docker system prune -f
EOF
    fi
    
    # Run health checks
    run_health_checks
    
    log_info "Production deployment completed successfully"
}

rollback() {
    log_info "Rolling back ${ENVIRONMENT} deployment..."
    
    if [ "${ENVIRONMENT}" == "production" ]; then
        # Confirmation prompt
        read -p "Are you sure you want to rollback PRODUCTION? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            log_warning "Rollback cancelled"
            exit 0
        fi
        
        if [ -n "${PRODUCTION_HOST}" ]; then
            ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} << EOF
                cd /opt/ohdsi
                docker-compose -f docker-compose.prod.yml down
                export IMAGE_TAG=latest
                docker-compose -f docker-compose.prod.yml up -d
EOF
        fi
    else
        cd "${PROJECT_ROOT}"
        docker-compose down
        docker-compose up -d
    fi
    
    log_info "Rollback completed"
}

get_status() {
    log_info "Getting status for ${ENVIRONMENT}..."
    
    if [ "${ENVIRONMENT}" == "local" ]; then
        cd "${PROJECT_ROOT}"
        docker-compose ps
        echo ""
        log_info "Health checks:"
        curl -s http://localhost:8000/health | jq '.' || echo "Backend health check failed"
        curl -s http://localhost:3000/api/health | jq '.' || echo "Frontend health check failed"
    elif [ -n "${PRODUCTION_HOST}" ] || [ -n "${STAGING_HOST}" ]; then
        HOST=${PRODUCTION_HOST:-${STAGING_HOST}}
        USER=${PRODUCTION_USER:-${STAGING_USER}}
        
        ssh ${USER}@${HOST} << EOF
            cd /opt/ohdsi
            docker-compose -f docker-compose.prod.yml ps
EOF
    fi
}

get_logs() {
    log_info "Getting logs for ${ENVIRONMENT}..."
    
    SERVICE=${3:-all}
    
    if [ "${ENVIRONMENT}" == "local" ]; then
        cd "${PROJECT_ROOT}"
        if [ "${SERVICE}" == "all" ]; then
            docker-compose logs --tail=100 -f
        else
            docker-compose logs --tail=100 -f ${SERVICE}
        fi
    elif [ -n "${PRODUCTION_HOST}" ] || [ -n "${STAGING_HOST}" ]; then
        HOST=${PRODUCTION_HOST:-${STAGING_HOST}}
        USER=${PRODUCTION_USER:-${STAGING_USER}}
        
        ssh ${USER}@${HOST} << EOF
            cd /opt/ohdsi
            if [ "${SERVICE}" == "all" ]; then
                docker-compose -f docker-compose.prod.yml logs --tail=100
            else
                docker-compose -f docker-compose.prod.yml logs --tail=100 ${SERVICE}
            fi
EOF
    fi
}

run_health_checks() {
    log_info "Running health checks..."
    
    if [ "${ENVIRONMENT}" == "local" ]; then
        BASE_URL="http://localhost:3000"
        API_URL="http://localhost:8000"
    elif [ "${ENVIRONMENT}" == "staging" ]; then
        BASE_URL="https://staging.ohdsi-dashboard.com"
        API_URL="https://staging.ohdsi-dashboard.com/api"
    else
        BASE_URL="https://ohdsi-dashboard.com"
        API_URL="https://ohdsi-dashboard.com/api"
    fi
    
    # Check frontend
    if curl -f -s "${BASE_URL}" > /dev/null; then
        log_info "Frontend is healthy"
    else
        log_error "Frontend health check failed"
    fi
    
    # Check backend
    if curl -f -s "${API_URL}/health" > /dev/null; then
        log_info "Backend is healthy"
    else
        log_error "Backend health check failed"
    fi
    
    # Check GraphQL
    if curl -f -s -X POST "${API_URL}/graphql" \
        -H "Content-Type: application/json" \
        -d '{"query":"{ __schema { queryType { name } } }"}' > /dev/null; then
        log_info "GraphQL is healthy"
    else
        log_error "GraphQL health check failed"
    fi
}

# Main execution
main() {
    log_info "OHDSI Dashboard Deployment Script"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Action: ${ACTION}"
    
    check_prerequisites
    
    case ${ACTION} in
        deploy)
            case ${ENVIRONMENT} in
                local)
                    deploy_local
                    ;;
                staging)
                    deploy_staging
                    ;;
                production)
                    deploy_production
                    ;;
                *)
                    log_error "Unknown environment: ${ENVIRONMENT}"
                    ;;
            esac
            ;;
        rollback)
            rollback
            ;;
        status)
            get_status
            ;;
        logs)
            get_logs
            ;;
        *)
            log_error "Unknown action: ${ACTION}"
            ;;
    esac
}

# Run main function
main