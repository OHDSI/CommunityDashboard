#!/bin/bash

# OHDSI Dashboard Health Check Script
# Systematically checks all components and reports errors

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Functions
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED_CHECKS++))
    ((TOTAL_CHECKS++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    echo "  Error: $2"
    ((FAILED_CHECKS++))
    ((TOTAL_CHECKS++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    echo "  Warning: $2"
    ((WARNINGS++))
}

section_header() {
    echo ""
    echo "========================================"
    echo "$1"
    echo "========================================"
}

# 1. Docker Container Health
section_header "1. DOCKER CONTAINER HEALTH"

services=("postgres:PostgreSQL" "elasticsearch:Elasticsearch" "redis:Redis" "backend:Backend" "frontend:Frontend")
for service_pair in "${services[@]}"; do
    IFS=':' read -r container_suffix display_name <<< "$service_pair"
    if docker ps | grep -q "ohdsi-$container_suffix"; then
        check_pass "Container $display_name is running"
    else
        check_fail "Container $display_name is not running" "Service is down or unhealthy"
    fi
done

# 2. Database Connectivity
section_header "2. DATABASE CONNECTIVITY"

# PostgreSQL
if docker exec ohdsi-postgres psql -U ohdsi_user ohdsi_dashboard -c "SELECT 1" > /dev/null 2>&1; then
    check_pass "PostgreSQL connection successful"
    
    # Check tables
    TABLE_COUNT=$(docker exec ohdsi-postgres psql -U ohdsi_user ohdsi_dashboard -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null | tr -d ' ')
    if [ "$TABLE_COUNT" -gt 0 ]; then
        check_pass "PostgreSQL has $TABLE_COUNT tables"
    else
        check_warn "PostgreSQL has no tables" "Database may need initialization"
    fi
    
    # Check users
    USER_COUNT=$(docker exec ohdsi-postgres psql -U ohdsi_user ohdsi_dashboard -t -c "SELECT COUNT(*) FROM users" 2>/dev/null | tr -d ' ' || echo "0")
    if [ "$USER_COUNT" -gt 0 ]; then
        check_pass "PostgreSQL has $USER_COUNT users"
    else
        check_warn "PostgreSQL has no users" "Run init_users.py to create default users"
    fi
else
    check_fail "PostgreSQL connection failed" "Cannot connect to database"
fi

# Elasticsearch
if curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
    check_pass "Elasticsearch connection successful"
    
    # Check indices
    if curl -s http://localhost:9200/_cat/indices 2>/dev/null | grep -q ohdsi_content; then
        check_pass "Elasticsearch ohdsi_content index exists"
        
        # Check document count
        DOC_COUNT=$(curl -s http://localhost:9200/ohdsi_content/_count 2>/dev/null | jq -r '.count' || echo "0")
        if [ "$DOC_COUNT" -gt 0 ]; then
            check_pass "Elasticsearch has $DOC_COUNT documents in ohdsi_content"
        else
            check_warn "Elasticsearch ohdsi_content index is empty" "Run sample_data_generator.py to load data"
        fi
    else
        check_fail "Elasticsearch ohdsi_content index missing" "Run setup_database.py to create indices"
    fi
else
    check_fail "Elasticsearch connection failed" "Cannot connect to Elasticsearch"
fi

# Redis
if docker exec ohdsi-redis redis-cli ping > /dev/null 2>&1; then
    check_pass "Redis connection successful"
else
    check_fail "Redis connection failed" "Cannot connect to Redis"
fi

# 3. Backend API Health
section_header "3. BACKEND API HEALTH"

# Health endpoint
if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    check_pass "Backend health endpoint responsive"
else
    check_fail "Backend health endpoint not responsive" "API may be down"
fi

# GraphQL endpoint
if curl -s -X POST http://localhost:8000/graphql \
    -H "Content-Type: application/json" \
    -d '{"query":"{ __schema { queryType { name } } }"}' | grep -q "Query"; then
    check_pass "GraphQL endpoint responsive"
else
    check_fail "GraphQL endpoint not responsive" "GraphQL may be misconfigured"
fi

# Test search query
SEARCH_RESULT=$(curl -s -X POST http://localhost:8000/graphql \
    -H "Content-Type: application/json" \
    -d '{"query":"{ searchContent(query: \"test\") { total } }"}' 2>/dev/null | jq -r '.data.searchContent.total' || echo "error")

if [ "$SEARCH_RESULT" != "error" ] && [ "$SEARCH_RESULT" != "null" ]; then
    check_pass "GraphQL search query works (found $SEARCH_RESULT items)"
else
    check_warn "GraphQL search query returned no results" "Elasticsearch may be empty or misconfigured"
fi

# Test authentication
AUTH_RESULT=$(curl -s -X POST http://localhost:8000/graphql \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"mutation { login(email: \\\"${ADMIN_EMAIL:-admin@ohdsi.org}\\\", password: \\\"${ADMIN_PASSWORD:-changeme}\\\") { accessToken } }\"}" 2>/dev/null | jq -r '.data.login.accessToken' || echo "error")

if [ "$AUTH_RESULT" != "error" ] && [ "$AUTH_RESULT" != "null" ]; then
    check_pass "Authentication system working"
else
    check_warn "Authentication failed" "Default users may not be created"
fi

# 4. Frontend Health
section_header "4. FRONTEND HEALTH"

# Frontend accessibility
if curl -f -s http://localhost:3000 > /dev/null 2>&1; then
    check_pass "Frontend is accessible"
else
    check_fail "Frontend not accessible" "Frontend server may be down"
fi

# Check for Next.js errors
if docker-compose logs frontend --tail=100 2>&1 | grep -q "Module not found\|Cannot find module"; then
    check_fail "Frontend has missing modules" "Some components may not be installed"
else
    check_pass "No missing module errors in frontend"
fi

if docker-compose logs frontend --tail=50 2>&1 | grep -q "Error"; then
    check_warn "Frontend has errors in logs" "Check frontend logs for details"
else
    check_pass "No errors in recent frontend logs"
fi

# Check API health endpoint
if curl -f -s http://localhost:3000/api/health > /dev/null 2>&1; then
    check_pass "Frontend API health endpoint responsive"
else
    check_warn "Frontend API health endpoint not responsive" "Health endpoint may not be configured"
fi

# 5. ML Classifier
section_header "5. ML CLASSIFIER"

# Check if classifier module can be imported
if docker-compose exec backend python -c "from jobs.article_classifier.classifier import OHDSIArticleClassifier; print('OK')" 2>/dev/null | grep -q "OK"; then
    check_pass "ML classifier module loads successfully"
else
    check_fail "ML classifier module failed to load" "Dependencies may be missing"
fi

# Check if model file exists
if docker-compose exec backend ls jobs/article_classifier/data/features.pkl > /dev/null 2>&1; then
    check_pass "ML model file exists"
else
    check_warn "ML model file missing" "Classifier may need training"
fi

# 6. Common Issues Check
section_header "6. COMMON ISSUES CHECK"

# Check for port conflicts
for port in 3000 8000 5432 9200 6379; do
    if lsof -i :$port | grep -q LISTEN; then
        check_pass "Port $port is in use (expected)"
    else
        check_warn "Port $port is not in use" "Service may not be running"
    fi
done

# Check disk space
DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 90 ]; then
    check_pass "Disk usage is ${DISK_USAGE}% (healthy)"
else
    check_warn "Disk usage is ${DISK_USAGE}%" "Low disk space may cause issues"
fi

# Check Docker daemon
if docker info > /dev/null 2>&1; then
    check_pass "Docker daemon is running"
else
    check_fail "Docker daemon not responding" "Docker may need to be restarted"
fi

# 7. Summary
section_header "HEALTH CHECK SUMMARY"

echo ""
echo "Total Checks: $TOTAL_CHECKS"
echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"
echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"

if [ $FAILED_CHECKS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All critical checks passed!${NC}"
    echo "The OHDSI Dashboard appears to be healthy."
else
    echo ""
    echo -e "${RED}✗ Some critical checks failed.${NC}"
    echo "Please review the errors above and run the following fixes:"
    echo ""
    echo "Common fixes:"
    echo "1. Restart services: docker-compose restart"
    echo "2. Initialize database: docker-compose exec backend python scripts/setup_database.py"
    echo "3. Create users: docker-compose exec backend python scripts/init_users.py"
    echo "4. Load sample data: docker-compose exec backend python scripts/sample_data_generator.py"
    echo "5. Check logs: docker-compose logs [service_name]"
fi

exit $FAILED_CHECKS