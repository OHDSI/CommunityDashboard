#!/bin/bash
# Kill any running ingestion processes to ensure clean slate

echo "============================================================"
echo "KILLING ANY EXISTING INGESTION PROCESSES"
echo "============================================================"

# Kill any Python ingestion scripts
echo "Checking for running ingestion scripts..."
PIDS=$(ps aux | grep -E "python.*ingest_|python.*pipeline|python.*fetch" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "✅ No ingestion processes found running"
else
    echo "Found the following ingestion processes:"
    ps aux | grep -E "python.*ingest_|python.*pipeline|python.*fetch" | grep -v grep
    
    echo ""
    echo "Killing processes..."
    for PID in $PIDS; do
        echo "  Killing PID $PID..."
        kill -9 $PID 2>/dev/null || echo "    (already dead or no permission)"
    done
    echo "✅ Processes killed"
fi

# Clear any Celery tasks
echo ""
echo "Purging any Celery queues..."
celery -A app.workers.celery_app purge -f 2>/dev/null || echo "  (Celery not accessible or no tasks)"

# Clear any lock files that might exist
echo ""
echo "Clearing any lock files..."
rm -f /tmp/*.lock 2>/dev/null
rm -f /app/logs/*.lock 2>/dev/null

echo ""
echo "============================================================"
echo "✅ CLEAN SLATE READY FOR NEW INGESTION"
echo "============================================================"
echo ""
echo "You can now run:"
echo "  1. Test script: python /app/scripts/test_enriched_citations.py"
echo "  2. Training data: python /app/scripts/ingest_training_data.py"
echo "  3. Multimodal: python /app/scripts/ingest_multimodal_content.py"