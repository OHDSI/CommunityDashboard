#!/bin/bash

# OHDSI Dashboard - Simple Azure VM Deployment Script
# This script creates a single Azure VM and deploys the application using Docker Compose
# Prerequisites: Azure CLI installed and logged in (az login)

set -e

# Configuration
RESOURCE_GROUP="OHDSI"  # Using your existing resource group
SUBSCRIPTION_ID=""  # Set your Azure subscription ID
VM_NAME="ohdsi-dashboard-vm"
LOCATION="eastus"  # Change if your resource group is in a different location
VM_SIZE="Standard_B2ms"  # 2 vCPUs, 8 GB RAM - good for small to medium workloads
ADMIN_USERNAME="azureuser"
DOMAIN_NAME=""  # Optional: Set your domain for SSL (e.g., "dashboard.ohdsi.org")

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}OHDSI Dashboard - Simple Azure Deployment${NC}"
echo "======================================"

# Check if user is logged into Azure
if ! az account show &>/dev/null; then
    echo -e "${RED}Error: Not logged into Azure. Please run 'az login' first.${NC}"
    exit 1
fi

# Set the subscription
echo -e "${YELLOW}Setting Azure subscription...${NC}"
az account set --subscription $SUBSCRIPTION_ID

# Get the current subscription
SUBSCRIPTION=$(az account show --query name -o tsv)
echo -e "${GREEN}Using Azure subscription: ${SUBSCRIPTION}${NC}"

# Verify resource group exists
echo -e "${YELLOW}Verifying resource group exists...${NC}"
if ! az group show --name $RESOURCE_GROUP &>/dev/null; then
    echo -e "${RED}Error: Resource group '$RESOURCE_GROUP' not found in subscription.${NC}"
    echo -e "${RED}Please check that the resource group exists or create it first.${NC}"
    exit 1
fi

# Get the location of the existing resource group
LOCATION=$(az group show --name $RESOURCE_GROUP --query location -o tsv)
echo -e "${GREEN}Using existing resource group '$RESOURCE_GROUP' in location '$LOCATION'${NC}"

# Prompt for domain name if not set
if [ -z "$DOMAIN_NAME" ]; then
    read -p "Enter domain name for SSL (optional, press Enter to skip): " DOMAIN_NAME
fi

# Create SSH key pair if it doesn't exist
SSH_KEY_PATH="$HOME/.ssh/ohdsi_azure_key"
if [ ! -f "$SSH_KEY_PATH" ]; then
    echo -e "${YELLOW}Creating SSH key pair...${NC}"
    ssh-keygen -t rsa -b 4096 -f $SSH_KEY_PATH -N "" -q
fi

# Create VM with Ubuntu 22.04 LTS
echo -e "${YELLOW}Creating Azure VM (this may take a few minutes)...${NC}"
az vm create \
    --resource-group $RESOURCE_GROUP \
    --name $VM_NAME \
    --image "Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:latest" \
    --size $VM_SIZE \
    --admin-username $ADMIN_USERNAME \
    --ssh-key-values $SSH_KEY_PATH.pub \
    --public-ip-address-allocation static \
    --public-ip-sku Standard

# Get the public IP address
PUBLIC_IP=$(az vm show -d -g $RESOURCE_GROUP -n $VM_NAME --query publicIps -o tsv)
echo -e "${GREEN}VM created with public IP: $PUBLIC_IP${NC}"

# Open required ports
echo -e "${YELLOW}Opening firewall ports...${NC}"
# Get the NSG name
NSG_NAME=$(az network nsg list --resource-group $RESOURCE_GROUP --query "[?contains(name, '$VM_NAME')].name" -o tsv)
echo -e "${GREEN}Using NSG: $NSG_NAME${NC}"

# HTTP and HTTPS
echo "Opening port 80 (HTTP)..."
az network nsg rule create --resource-group $RESOURCE_GROUP --nsg-name $NSG_NAME \
    --name allow-http --protocol tcp --priority 1010 --destination-port-range 80 \
    --access allow --direction inbound --source-address-prefixes '*' --destination-address-prefixes '*'

echo "Opening port 443 (HTTPS)..."
az network nsg rule create --resource-group $RESOURCE_GROUP --nsg-name $NSG_NAME \
    --name allow-https --protocol tcp --priority 1020 --destination-port-range 443 \
    --access allow --direction inbound --source-address-prefixes '*' --destination-address-prefixes '*'

# Application ports (can be removed if using reverse proxy)
echo "Opening port 3000 (Frontend)..."
az network nsg rule create --resource-group $RESOURCE_GROUP --nsg-name $NSG_NAME \
    --name allow-frontend --protocol tcp --priority 1030 --destination-port-range 3000 \
    --access allow --direction inbound --source-address-prefixes '*' --destination-address-prefixes '*'

echo "Opening port 8000 (Backend API)..."
az network nsg rule create --resource-group $RESOURCE_GROUP --nsg-name $NSG_NAME \
    --name allow-backend --protocol tcp --priority 1040 --destination-port-range 8000 \
    --access allow --direction inbound --source-address-prefixes '*' --destination-address-prefixes '*'

# Create deployment script to run on VM
cat > /tmp/setup_ohdsi.sh << 'SETUP_SCRIPT'
#!/bin/bash
set -e

echo "Starting OHDSI Dashboard setup..."

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo "Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
echo "Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install git
sudo apt-get install -y git

# Clone the repository (you'll need to update this with your repo URL)
echo "Cloning repository..."
cd /home/$USER
if [ ! -d "ohdsi-dashboard" ]; then
    git clone https://github.com/yourusername/ohdsi-dashboard.git
fi
cd ohdsi-dashboard

# Copy production environment file
if [ ! -f .env ]; then
    cp .env.production .env
    echo "Please edit .env file with your API keys and configuration"
fi

# Create necessary directories
mkdir -p data/postgres
mkdir -p data/elasticsearch
mkdir -p data/redis

# Set proper permissions
sudo chown -R 1000:1000 data/elasticsearch

# Start services with Docker Compose
echo "Starting services..."
sudo docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 30

# Initialize database
echo "Initializing database..."
sudo docker-compose -f docker-compose.prod.yml exec -T backend python scripts/setup_database.py
sudo docker-compose -f docker-compose.prod.yml exec -T backend python scripts/init_users.py

echo "Setup complete!"
echo "Application should be accessible at http://$PUBLIC_IP:3000"
echo ""
echo "Next steps:"
echo "1. Edit /home/$USER/ohdsi-dashboard/.env with your API keys"
echo "2. Restart services: cd /home/$USER/ohdsi-dashboard && sudo docker-compose -f docker-compose.prod.yml restart"
echo "3. Check logs: sudo docker-compose -f docker-compose.prod.yml logs -f"
SETUP_SCRIPT

# Replace $USER and $PUBLIC_IP in the script
sed -i "s/\$USER/$ADMIN_USERNAME/g" /tmp/setup_ohdsi.sh
sed -i "s/\$PUBLIC_IP/$PUBLIC_IP/g" /tmp/setup_ohdsi.sh

# Copy setup script to VM
echo -e "${YELLOW}Copying setup script to VM...${NC}"
scp -i $SSH_KEY_PATH -o StrictHostKeyChecking=no /tmp/setup_ohdsi.sh $ADMIN_USERNAME@$PUBLIC_IP:/tmp/

# Copy docker-compose.prod.yml if it exists locally
if [ -f "docker-compose.prod.yml" ]; then
    echo -e "${YELLOW}Copying docker-compose.prod.yml to VM...${NC}"
    scp -i $SSH_KEY_PATH -o StrictHostKeyChecking=no docker-compose.prod.yml $ADMIN_USERNAME@$PUBLIC_IP:/tmp/
fi

# Copy .env.production if it exists locally
if [ -f ".env.production" ]; then
    echo -e "${YELLOW}Copying .env.production to VM...${NC}"
    scp -i $SSH_KEY_PATH -o StrictHostKeyChecking=no .env.production $ADMIN_USERNAME@$PUBLIC_IP:/tmp/
fi

# Execute setup script on VM
echo -e "${YELLOW}Running setup on VM (this will take several minutes)...${NC}"
ssh -i $SSH_KEY_PATH -o StrictHostKeyChecking=no $ADMIN_USERNAME@$PUBLIC_IP "chmod +x /tmp/setup_ohdsi.sh && /tmp/setup_ohdsi.sh"

# Optional: Setup SSL with Let's Encrypt
if [ ! -z "$DOMAIN_NAME" ]; then
    echo -e "${YELLOW}Setting up SSL for $DOMAIN_NAME...${NC}"
    
    # Create SSL setup script
    cat > /tmp/setup_ssl.sh << SSL_SCRIPT
#!/bin/bash
sudo apt-get install -y certbot python3-certbot-nginx nginx

# Create nginx config
sudo tee /etc/nginx/sites-available/ohdsi-dashboard << NGINX_CONFIG
server {
    listen 80;
    server_name $DOMAIN_NAME;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \\\$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \\\$host;
        proxy_cache_bypass \\\$http_upgrade;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
    }

    location /graphql {
        proxy_pass http://localhost:8000/graphql;
        proxy_http_version 1.1;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
    }
}
NGINX_CONFIG

sudo ln -s /etc/nginx/sites-available/ohdsi-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate
sudo certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME
SSL_SCRIPT

    # Copy and run SSL setup
    scp -i $SSH_KEY_PATH -o StrictHostKeyChecking=no /tmp/setup_ssl.sh $ADMIN_USERNAME@$PUBLIC_IP:/tmp/
    ssh -i $SSH_KEY_PATH $ADMIN_USERNAME@$PUBLIC_IP "chmod +x /tmp/setup_ssl.sh && /tmp/setup_ssl.sh"
fi

# Clean up temporary files
rm -f /tmp/setup_ohdsi.sh /tmp/setup_ssl.sh

echo ""
echo -e "${GREEN}======================================"
echo -e "Deployment Complete!"
echo -e "======================================${NC}"
echo ""
echo "VM Details:"
echo "  Name: $VM_NAME"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Location: $LOCATION"
echo "  Subscription: $SUBSCRIPTION_ID"
echo "  Public IP: $PUBLIC_IP"
echo "  SSH Key: $SSH_KEY_PATH"
echo ""
echo "Access the application:"
if [ ! -z "$DOMAIN_NAME" ]; then
    echo "  https://$DOMAIN_NAME"
else
    echo "  http://$PUBLIC_IP:3000 (Frontend)"
    echo "  http://$PUBLIC_IP:8000 (Backend API)"
fi
echo ""
echo "SSH to VM:"
echo "  ssh -i $SSH_KEY_PATH $ADMIN_USERNAME@$PUBLIC_IP"
echo ""
echo "Manage services:"
echo "  ssh -i $SSH_KEY_PATH $ADMIN_USERNAME@$PUBLIC_IP"
echo "  cd ohdsi-dashboard"
echo "  sudo docker-compose -f docker-compose.prod.yml ps"
echo "  sudo docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo -e "${YELLOW}IMPORTANT: Remember to:"
echo "1. Update .env file with your API keys"
echo "2. Configure your DNS to point to $PUBLIC_IP"
echo "3. Review and adjust firewall rules as needed${NC}"