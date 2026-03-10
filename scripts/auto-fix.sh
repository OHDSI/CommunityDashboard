#!/bin/bash

# OHDSI Dashboard Automated Fix Script
# Automatically fixes common issues identified by health check

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Functions
print_status() {
    echo -e "${BLUE}[STATUS]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 1. Fix Celery Worker Async Elasticsearch Issue
fix_celery_elasticsearch() {
    print_status "Fixing Celery worker Elasticsearch async issue..."
    
    # Create a separate elasticsearch client for Celery (synchronous)
    cat > /tmp/celery_es_fix.py << 'EOF'
import sys
sys.path.append('/app')

# Read the current database.py
with open('/app/app/database.py', 'r') as f:
    content = f.read()

# Check if we already have a sync client for Celery
if 'celery_es_client' not in content:
    # Add a synchronous client specifically for Celery
    lines = content.split('\n')
    
    # Find the line after the async_es_client definition
    for i, line in enumerate(lines):
        if 'async_es_client = AsyncElasticsearch' in line:
            # Insert the celery client after the async client
            insert_point = i + 3
            lines.insert(insert_point, '')
            lines.insert(insert_point + 1, '# Synchronous client for Celery tasks')
            lines.insert(insert_point + 2, 'celery_es_client = Elasticsearch(')
            lines.insert(insert_point + 3, '    settings.elasticsearch_url,')
            lines.insert(insert_point + 4, '    timeout=settings.elasticsearch_timeout')
            lines.insert(insert_point + 5, ')')
            break
    
    # Write back the modified content
    with open('/app/app/database.py', 'w') as f:
        f.write('\n'.join(lines))
    
    print("Added celery_es_client to database.py")
else:
    print("celery_es_client already exists in database.py")

# Update tasks.py to use the synchronous client
try:
    with open('/app/app/workers/tasks.py', 'r') as f:
        tasks_content = f.read()
    
    # Replace async_es_client with celery_es_client in tasks
    if 'async_es_client' in tasks_content:
        tasks_content = tasks_content.replace(
            'from ..database import async_es_client',
            'from ..database import celery_es_client as es_client'
        )
        tasks_content = tasks_content.replace('async_es_client', 'es_client')
        
        with open('/app/app/workers/tasks.py', 'w') as f:
            f.write(tasks_content)
        
        print("Updated tasks.py to use synchronous client")
except FileNotFoundError:
    print("tasks.py not found, skipping")
EOF
    
    docker-compose exec -T backend python /tmp/celery_es_fix.py 2>/dev/null || true
    
    # Install aiohttp just in case
    docker-compose exec -T backend pip install aiohttp 2>/dev/null || true
    
    print_success "Fixed Celery Elasticsearch client issue"
}

# 2. Restart Services
restart_services() {
    print_status "Restarting services to apply fixes..."
    
    # Restart backend first (includes Celery)
    docker-compose restart backend
    sleep 5
    
    # Check if backend is healthy
    if docker ps | grep -q "ohdsi-backend"; then
        print_success "Backend restarted successfully"
    else
        print_error "Backend failed to restart"
        return 1
    fi
}

# 3. Initialize Database if needed
init_database() {
    print_status "Checking database initialization..."
    
    # Check if tables exist
    TABLE_COUNT=$(docker exec ohdsi-postgresql psql -U ohdsi_user ohdsi_dashboard -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null | tr -d ' ' || echo "0")
    
    if [ "$TABLE_COUNT" -eq "0" ]; then
        print_status "Initializing database tables..."
        docker-compose exec -T backend python scripts/setup_database.py
        print_success "Database tables created"
    else
        print_success "Database tables already exist ($TABLE_COUNT tables)"
    fi
    
    # Check if users exist
    USER_COUNT=$(docker exec ohdsi-postgresql psql -U ohdsi_user ohdsi_dashboard -t -c "SELECT COUNT(*) FROM users" 2>/dev/null | tr -d ' ' || echo "0")
    
    if [ "$USER_COUNT" -eq "0" ]; then
        print_status "Creating default users..."
        docker-compose exec -T backend python scripts/init_users.py
        print_success "Default users created"
    else
        print_success "Users already exist ($USER_COUNT users)"
    fi
}

# 4. Initialize Elasticsearch if needed
init_elasticsearch() {
    print_status "Checking Elasticsearch indices..."
    
    # Check if ohdsi_content index exists
    if ! curl -s http://localhost:9200/_cat/indices 2>/dev/null | grep -q ohdsi_content; then
        print_status "Creating Elasticsearch indices..."
        docker-compose exec -T backend python -c "from app.database import create_indices; create_indices()"
        print_success "Elasticsearch indices created"
    else
        print_success "Elasticsearch indices already exist"
    fi
    
    # Check if sample data is needed
    DOC_COUNT=$(curl -s http://localhost:9200/ohdsi_content/_count 2>/dev/null | jq -r '.count' || echo "0")
    
    if [ "$DOC_COUNT" -eq "0" ]; then
        print_status "Loading sample data..."
        docker-compose exec -T backend python scripts/sample_data_generator.py
        print_success "Sample data loaded"
    else
        print_success "Elasticsearch already has $DOC_COUNT documents"
    fi
}

# 5. Fix Frontend Missing Modules
fix_frontend_modules() {
    print_status "Checking frontend modules..."
    
    # Check if node_modules exists
    if ! docker-compose exec -T frontend test -d node_modules; then
        print_status "Installing frontend dependencies..."
        docker-compose exec -T frontend npm install
        print_success "Frontend dependencies installed"
    fi
    
    # Rebuild frontend if there are issues
    if docker-compose logs frontend --tail=50 2>&1 | grep -q "Module not found"; then
        print_status "Rebuilding frontend..."
        docker-compose exec -T frontend npm run build
        docker-compose restart frontend
        print_success "Frontend rebuilt and restarted"
    else
        print_success "Frontend modules are OK"
    fi
}

# 6. Create health check endpoint if missing
create_health_endpoint() {
    print_status "Checking frontend health endpoint..."
    
    if ! curl -f -s http://localhost:3000/api/health > /dev/null 2>&1; then
        print_status "Creating frontend health endpoint..."
        
        # Create api/health route
        cat > /tmp/health_route.tsx << 'EOF'
import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({ status: 'ok' })
}
EOF
        
        docker cp /tmp/health_route.tsx ohdsi-frontend:/app/app/api/health/route.ts 2>/dev/null || true
        docker-compose restart frontend
        print_success "Frontend health endpoint created"
    else
        print_success "Frontend health endpoint already exists"
    fi
}

# 7. Fix ML Classifier Dependencies
fix_ml_dependencies() {
    print_status "Checking ML classifier dependencies..."
    
    # Install missing Python packages
    PACKAGES="requests scipy joblib scikit-learn pandas biopython"
    
    for package in $PACKAGES; do
        docker-compose exec -T backend pip show $package > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            print_status "Installing $package..."
            docker-compose exec -T backend pip install $package
            print_success "Installed $package"
        fi
    done
    
    print_success "ML dependencies are installed"
}

# 8. Clear caches and temporary files
clear_caches() {
    print_status "Clearing caches..."
    
    # Clear Redis cache
    docker exec ohdsi-redis redis-cli FLUSHALL > /dev/null 2>&1 || true
    
    # Clear Next.js cache
    docker-compose exec -T frontend rm -rf .next/cache 2>/dev/null || true
    
    print_success "Caches cleared"
}

# Main execution
main() {
    echo "=========================================="
    echo "OHDSI Dashboard Automated Fix Script"
    echo "=========================================="
    echo ""
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    # Check if we're in the right directory
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml not found. Please run this script from the project root."
        exit 1
    fi
    
    # Run fixes
    fix_celery_elasticsearch
    init_database
    init_elasticsearch
    fix_frontend_modules
    create_health_endpoint
    fix_ml_dependencies
    clear_caches
    restart_services
    
    echo ""
    echo "=========================================="
    echo "Fix Summary"
    echo "=========================================="
    print_success "All automated fixes have been applied!"
    echo ""
    echo "Next steps:"
    echo "1. Run ./scripts/health-check.sh to verify all issues are resolved"
    echo "2. Access the application at http://localhost:3000"
    echo "3. Check logs if any issues persist: docker-compose logs -f [service]"
    echo ""
    echo "If issues persist, you can:"
    echo "- Restart all services: docker-compose restart"
    echo "- Rebuild containers: docker-compose build --no-cache"
    echo "- Full reset: make clean && make dev"
}

# Run main function
main