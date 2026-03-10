#!/bin/bash

# Script to open ports for existing OHDSI Dashboard VM
# Run this after VM is created if ports weren't opened during initial deployment

set -e

# Configuration
RESOURCE_GROUP="OHDSI"
VM_NAME="ohdsi-dashboard-vm"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Opening ports for OHDSI Dashboard VM${NC}"
echo "======================================"

# Get the NSG name
echo -e "${YELLOW}Finding Network Security Group...${NC}"
NSG_NAME=$(az network nsg list --resource-group $RESOURCE_GROUP --query "[?contains(name, '$VM_NAME')].name" -o tsv)

if [ -z "$NSG_NAME" ]; then
    echo -e "${RED}Error: Could not find NSG for VM $VM_NAME${NC}"
    exit 1
fi

echo -e "${GREEN}Using NSG: $NSG_NAME${NC}"

# List existing rules
echo -e "${YELLOW}Existing security rules:${NC}"
az network nsg rule list --resource-group $RESOURCE_GROUP --nsg-name $NSG_NAME --output table

# Open ports with unique priorities
echo -e "${YELLOW}Opening required ports...${NC}"

# HTTP
echo "Opening port 80 (HTTP)..."
az network nsg rule create --resource-group $RESOURCE_GROUP --nsg-name $NSG_NAME \
    --name allow-http --protocol tcp --priority 1010 --destination-port-range 80 \
    --access allow --direction inbound --source-address-prefixes '*' --destination-address-prefixes '*' \
    2>/dev/null || echo "Port 80 rule already exists"

# HTTPS
echo "Opening port 443 (HTTPS)..."
az network nsg rule create --resource-group $RESOURCE_GROUP --nsg-name $NSG_NAME \
    --name allow-https --protocol tcp --priority 1020 --destination-port-range 443 \
    --access allow --direction inbound --source-address-prefixes '*' --destination-address-prefixes '*' \
    2>/dev/null || echo "Port 443 rule already exists"

# Frontend
echo "Opening port 3000 (Frontend)..."
az network nsg rule create --resource-group $RESOURCE_GROUP --nsg-name $NSG_NAME \
    --name allow-frontend --protocol tcp --priority 1030 --destination-port-range 3000 \
    --access allow --direction inbound --source-address-prefixes '*' --destination-address-prefixes '*' \
    2>/dev/null || echo "Port 3000 rule already exists"

# Backend API
echo "Opening port 8000 (Backend API)..."
az network nsg rule create --resource-group $RESOURCE_GROUP --nsg-name $NSG_NAME \
    --name allow-backend --protocol tcp --priority 1040 --destination-port-range 8000 \
    --access allow --direction inbound --source-address-prefixes '*' --destination-address-prefixes '*' \
    2>/dev/null || echo "Port 8000 rule already exists"

echo ""
echo -e "${GREEN}======================================"
echo -e "Port Configuration Complete!"
echo -e "======================================${NC}"
echo ""
echo "Updated security rules:"
az network nsg rule list --resource-group $RESOURCE_GROUP --nsg-name $NSG_NAME --output table

echo ""
echo "Your application will be accessible at:"
echo "  Frontend: http://YOUR_VM_IP:3000"
echo "  Backend API: http://YOUR_VM_IP:8000"
echo "  GraphQL: http://YOUR_VM_IP:8000/graphql"