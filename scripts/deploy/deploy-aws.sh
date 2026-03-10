#!/bin/bash

# AWS ECS Deployment Script for OHDSI Dashboard
# Prerequisites: AWS CLI configured, ECS cluster created

set -e

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
ECR_REGISTRY=${ECR_REGISTRY:-}
ECS_CLUSTER=${ECS_CLUSTER:-ohdsi-cluster}
ECS_SERVICE_BACKEND=${ECS_SERVICE_BACKEND:-ohdsi-backend-service}
ECS_SERVICE_FRONTEND=${ECS_SERVICE_FRONTEND:-ohdsi-frontend-service}
ENVIRONMENT=${1:-staging}

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check AWS CLI
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured"
    fi
    
    log_info "AWS CLI configured successfully"
}

# Login to ECR
login_ecr() {
    log_info "Logging in to Amazon ECR..."
    aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
}

# Build and push images
build_and_push() {
    local SERVICE=$1
    local DOCKERFILE=$2
    local CONTEXT=$3
    local TAG=${ENVIRONMENT}-$(git rev-parse --short HEAD)
    
    log_info "Building ${SERVICE} image..."
    docker build -f ${DOCKERFILE} -t ${SERVICE}:${TAG} ${CONTEXT}
    
    log_info "Tagging image for ECR..."
    docker tag ${SERVICE}:${TAG} ${ECR_REGISTRY}/${SERVICE}:${TAG}
    docker tag ${SERVICE}:${TAG} ${ECR_REGISTRY}/${SERVICE}:${ENVIRONMENT}-latest
    
    log_info "Pushing ${SERVICE} to ECR..."
    docker push ${ECR_REGISTRY}/${SERVICE}:${TAG}
    docker push ${ECR_REGISTRY}/${SERVICE}:${ENVIRONMENT}-latest
}

# Update ECS service
update_ecs_service() {
    local SERVICE=$1
    local TASK_DEFINITION=$2
    
    log_info "Updating ECS service ${SERVICE}..."
    
    # Register new task definition
    aws ecs register-task-definition \
        --cli-input-json file://.aws/task-definitions/${TASK_DEFINITION}.json \
        --region ${AWS_REGION}
    
    # Update service with new task definition
    aws ecs update-service \
        --cluster ${ECS_CLUSTER} \
        --service ${SERVICE} \
        --task-definition ${TASK_DEFINITION} \
        --force-new-deployment \
        --region ${AWS_REGION}
    
    log_info "Waiting for service ${SERVICE} to stabilize..."
    aws ecs wait services-stable \
        --cluster ${ECS_CLUSTER} \
        --services ${SERVICE} \
        --region ${AWS_REGION}
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Run migration task
    aws ecs run-task \
        --cluster ${ECS_CLUSTER} \
        --task-definition ohdsi-migrations \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[${PRIVATE_SUBNETS}],securityGroups=[${SECURITY_GROUP}],assignPublicIp=DISABLED}" \
        --region ${AWS_REGION}
    
    # Wait for task to complete
    sleep 30
}

# Main deployment
main() {
    log_info "Starting AWS ECS deployment for ${ENVIRONMENT}"
    
    # Validate environment
    check_aws_cli
    
    # Login to ECR
    login_ecr
    
    # Build and push backend
    build_and_push "ohdsi-backend" "backend/Dockerfile" "backend"
    
    # Build and push frontend
    build_and_push "ohdsi-frontend" "frontend/Dockerfile" "frontend"
    
    # Update ECS services
    update_ecs_service ${ECS_SERVICE_BACKEND} "ohdsi-backend-task"
    update_ecs_service ${ECS_SERVICE_FRONTEND} "ohdsi-frontend-task"
    
    # Run migrations
    run_migrations
    
    log_info "Deployment completed successfully!"
    
    # Get service endpoints
    log_info "Service endpoints:"
    aws ecs describe-services \
        --cluster ${ECS_CLUSTER} \
        --services ${ECS_SERVICE_BACKEND} ${ECS_SERVICE_FRONTEND} \
        --query 'services[*].loadBalancers[0].dnsName' \
        --output table \
        --region ${AWS_REGION}
}

# Run main
main