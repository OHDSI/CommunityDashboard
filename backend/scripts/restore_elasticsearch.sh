#!/bin/bash

# Restore Elasticsearch data from backup
if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file>"
    echo "Available backups:"
    ls -lh /home/azureuser/backups/elasticsearch_volume_*.tar.gz 2>/dev/null
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file $BACKUP_FILE not found!"
    exit 1
fi

echo "WARNING: This will replace all current Elasticsearch data!"
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 1
fi

echo "Stopping Elasticsearch container..."
docker stop ohdsi-elasticsearch

echo "Restoring from backup: $BACKUP_FILE"
docker run --rm -v ohdsi-dashboard_elasticsearch_data:/data -v $(dirname $BACKUP_FILE):/backup alpine sh -c "rm -rf /data/* && tar xzf /backup/$(basename $BACKUP_FILE) -C /data"

echo "Starting Elasticsearch container..."
docker start ohdsi-elasticsearch

echo "Waiting for Elasticsearch to be ready..."
sleep 10

# Check if Elasticsearch is responding
curl -s "http://localhost:9200/_cluster/health" | python3 -m json.tool

echo "Restore completed!"
echo "Checking indices..."
curl -s "http://localhost:9200/_cat/indices?v"