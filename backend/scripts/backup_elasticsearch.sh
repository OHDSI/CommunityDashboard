#!/bin/bash

# Backup Elasticsearch data
echo "Creating Elasticsearch backup..."

BACKUP_DIR="/home/azureuser/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/elasticsearch_backup_$TIMESTAMP.tar.gz"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create backup using Elasticsearch snapshot API
echo "Creating snapshot via Elasticsearch API..."
curl -X PUT "localhost:9200/_snapshot/backup_repo" -H 'Content-Type: application/json' -d'{
  "type": "fs",
  "settings": {
    "location": "/usr/share/elasticsearch/backup"
  }
}' 2>/dev/null

# Take snapshot
curl -X PUT "localhost:9200/_snapshot/backup_repo/snapshot_$TIMESTAMP?wait_for_completion=true" 2>/dev/null

# Also create a volume backup
echo "Creating volume backup..."
docker run --rm -v ohdsi-dashboard_elasticsearch_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/elasticsearch_volume_$TIMESTAMP.tar.gz -C /data .

echo "Backup completed: $BACKUP_DIR/elasticsearch_volume_$TIMESTAMP.tar.gz"

# Keep only last 5 backups
echo "Cleaning old backups..."
ls -t $BACKUP_DIR/elasticsearch_volume_*.tar.gz | tail -n +6 | xargs -r rm

echo "Done! Current backups:"
ls -lh $BACKUP_DIR/*.tar.gz