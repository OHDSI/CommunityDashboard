# OHDSI Dashboard - Simple Azure Deployment Guide

This guide provides a minimal complexity deployment of the OHDSI Dashboard to Azure using a single VM with Docker Compose.

## Prerequisites

1. **Azure Account**: Active Azure subscription with existing resource group
2. **Azure CLI**: Install from [here](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
3. **Local Setup**: Clone this repository locally
4. **Domain Name** (Optional): For SSL setup

**Note**: Update the subscription ID and resource group in `scripts/azure-deploy-simple.sh` before running.

## Quick Start (3 Steps)

### Step 1: Deploy to Azure

```bash
# Login to Azure
az login

# Run deployment script
cd scripts
chmod +x azure-deploy-simple.sh
./azure-deploy-simple.sh
```

**Note**: If the VM is already created (IP: YOUR_VM_IP), skip to Step 1b below.

The script will:
- Create a VM in your existing OHDSI resource group (Standard_B2ms: 2 vCPUs, 8GB RAM)
- Install Docker and Docker Compose
- Deploy all services
- Output the VM's public IP address

### Step 1b: If VM Already Exists (Continue Setup)

If your VM is already created at IP YOUR_VM_IP, open the ports and continue setup:

```bash
# Open firewall ports
cd scripts
chmod +x azure-open-ports.sh
./azure-open-ports.sh

# SSH to VM and continue setup
ssh -i ~/.ssh/your_ssh_key azureuser@YOUR_VM_IP
```

Then run the setup on the VM:
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install git and clone repository
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/yourusername/ohdsi-dashboard.git
cd ohdsi-dashboard

# Copy production environment
cp .env.production .env
nano .env  # Edit with your configuration

# Start services
sudo docker-compose -f docker-compose.prod.yml up -d
```

### Step 2: Configure Environment

SSH into your VM and update the configuration:

```bash
# SSH to VM (the script shows you the exact command)
ssh -i ~/.ssh/your_ssh_key azureuser@YOUR_VM_IP

# Edit environment variables
cd ohdsi-dashboard
nano .env

# Update these required fields:
# - POSTGRES_PASSWORD (use a strong password)
# - SECRET_KEY (generate with: openssl rand -hex 32)
# - NCBI_ENTREZ_EMAIL (your email for PubMed API)
# - Domain URLs (replace your-domain.com with VM IP or domain)

# Restart services after configuration
sudo docker-compose -f docker-compose.prod.yml restart
```

### Step 3: Access Application

With your current VM at YOUR_VM_IP:
- **Frontend**: `http://YOUR_VM_IP:3000`
- **Backend API**: `http://YOUR_VM_IP:8000`
- **GraphQL Playground**: `http://YOUR_VM_IP:8000/graphql`

## Configuration Details

### Essential Configuration (.env)

```bash
# MUST CHANGE - Security
POSTGRES_PASSWORD=your_secure_password_here
SECRET_KEY=generate_with_openssl_rand_hex_32

# MUST CHANGE - URLs (use your VM IP or domain)
NEXT_PUBLIC_API_URL=http://YOUR_VM_IP:8000
NEXT_PUBLIC_GRAPHQL_URL=http://YOUR_VM_IP:8000/graphql
BASE_URL=http://YOUR_VM_IP:8000
FRONTEND_URL=http://YOUR_VM_IP:3000
CORS_ORIGINS=["http://YOUR_VM_IP:3000"]

# Required for PubMed content
NCBI_ENTREZ_EMAIL=your_email@example.com
```

### Optional API Keys

Add these for additional content sources:

```bash
# GitHub repositories (optional)
GITHUB_TOKEN=your_github_token

# YouTube videos (optional)
YOUTUBE_API_KEY=your_youtube_api_key

# AI enhancements (optional)
OPENAI_API_KEY=your_openai_api_key
```

## VM Management

### Check Service Status

```bash
ssh -i ~/.ssh/your_ssh_key azureuser@YOUR_VM_IP
cd ohdsi-dashboard
sudo docker-compose -f docker-compose.prod.yml ps
```

### View Logs

```bash
# All services
sudo docker-compose -f docker-compose.prod.yml logs -f

# Specific service
sudo docker-compose -f docker-compose.prod.yml logs -f backend
```

### Restart Services

```bash
sudo docker-compose -f docker-compose.prod.yml restart
```

### Stop Services

```bash
sudo docker-compose -f docker-compose.prod.yml down
```

### Start Services

```bash
sudo docker-compose -f docker-compose.prod.yml up -d
```

## Optional: SSL Setup with Domain

If you have a domain name:

1. Point your domain to the VM's public IP
2. Run the deployment script with domain:
   ```bash
   # When prompted, enter your domain name
   ./azure-deploy-simple.sh
   # Enter domain: dashboard.example.com
   ```
3. The script will automatically:
   - Install Nginx as reverse proxy
   - Configure Let's Encrypt SSL certificate
   - Set up auto-renewal

## Data Management

### Backup Database

```bash
ssh -i ~/.ssh/your_ssh_key azureuser@YOUR_VM_IP
cd ohdsi-dashboard

# Create backup
sudo docker-compose -f docker-compose.prod.yml exec postgresql \
  pg_dump -U ohdsi_user ohdsi_dashboard > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
# Copy backup to VM
scp -i ~/.ssh/your_ssh_key backup.sql azureuser@YOUR_VM_IP:/tmp/

# Restore
ssh -i ~/.ssh/your_ssh_key azureuser@YOUR_VM_IP
cd ohdsi-dashboard
cat /tmp/backup.sql | sudo docker-compose -f docker-compose.prod.yml exec -T postgresql \
  psql -U ohdsi_user ohdsi_dashboard
```

## Update Application

```bash
ssh -i ~/.ssh/your_ssh_key azureuser@YOUR_VM_IP
cd ohdsi-dashboard

# Pull latest code
git pull

# Rebuild and restart
sudo docker-compose -f docker-compose.prod.yml build
sudo docker-compose -f docker-compose.prod.yml up -d
```

## VM Specifications

The default VM (Standard_B2ms) provides:
- 2 vCPUs
- 8 GB RAM
- 16 GB temporary storage
- ~$60/month cost

For larger deployments, edit `azure-deploy-simple.sh` and change:
```bash
VM_SIZE="Standard_B4ms"  # 4 vCPUs, 16 GB RAM
# or
VM_SIZE="Standard_D2s_v3"  # 2 vCPUs, 8 GB RAM, better performance
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs
sudo docker-compose -f docker-compose.prod.yml logs

# Check disk space
df -h

# Check memory
free -h

# Restart Docker
sudo systemctl restart docker
```

### Can't Access Application

```bash
# Check if services are running
sudo docker-compose -f docker-compose.prod.yml ps

# Check firewall rules (on Azure Portal)
# Ensure ports 80, 443, 3000, 8000 are open

# Test locally on VM
curl http://localhost:3000
curl http://localhost:8000/health
```

### Database Connection Issues

```bash
# Test database connection
sudo docker-compose -f docker-compose.prod.yml exec backend \
  python -c "from app.database import SessionLocal; db = SessionLocal(); print('Connected!')"
```

## Clean Up

To remove the VM deployment (keeping the resource group):

```bash
# Delete just the VM and its resources
az vm delete --resource-group OHDSI --name ohdsi-dashboard-vm --yes
az network public-ip delete --resource-group OHDSI --name ohdsi-dashboard-vmPublicIP
az network nic delete --resource-group OHDSI --name ohdsi-dashboard-vmVMNic
az disk delete --resource-group OHDSI --name ohdsi-dashboard-vm_OsDisk --yes

# Remove local SSH key
rm ~/.ssh/your_ssh_key*
```

## Cost Optimization

- **Development**: Use B1s (1 vCPU, 1 GB RAM) - ~$10/month
- **Production**: Use B2ms (2 vCPUs, 8 GB RAM) - ~$60/month
- **Auto-shutdown**: Configure VM to stop during non-business hours
- **Reserved Instances**: Save up to 72% with 1-3 year commitment

## Security Checklist

- [ ] Changed default passwords
- [ ] Generated new SECRET_KEY
- [ ] Configured firewall rules
- [ ] Enabled SSL (if using domain)
- [ ] Regular backups configured
- [ ] Monitoring enabled
- [ ] SSH key secured

## Support

For issues or questions:
1. Check application logs: `sudo docker-compose -f docker-compose.prod.yml logs`
2. Review this guide's troubleshooting section
3. Check Azure VM diagnostics in Azure Portal

## Next Steps

1. **Configure SSO**: Add Google/GitHub OAuth for easier login
2. **Enable Monitoring**: Add Sentry or New Relic keys
3. **Set Up Backups**: Configure automated database backups
4. **Scale Up**: Upgrade VM size if needed
5. **Add CDN**: Use Azure CDN for static assets