# Independent Ingestion Scripts - Command Reference

## Quick Start

All scripts follow the same basic pattern:
```bash
docker-compose exec backend python /app/scripts/ingest/ingest_[source].py --max-items [N] [options]
```

## PubMed Articles

### Basic Usage
```bash
# Fetch 100 recent articles
docker-compose exec backend python /app/scripts/ingest/ingest_pubmed.py --max-items 100

# Fetch articles from specific date range
docker-compose exec backend python /app/scripts/ingest/ingest_pubmed.py \
    --max-items 50 \
    --date-from 2025-01-01 \
    --date-to 2025-08-10

# Test with dry-run (no indexing)
docker-compose exec backend python /app/scripts/ingest/ingest_pubmed.py \
    --max-items 5 \
    --dry-run

# Enable AI enhancement
docker-compose exec backend python /app/scripts/ingest/ingest_pubmed.py \
    --max-items 50 \
    --enable-ai
```

### Features
- Fetches OHDSI-related articles from PubMed
- Includes enriched citation metadata (title, year, journal, authors)
- Searches multiple OHDSI-specific queries
- Auto-approval threshold: 0.7

## YouTube Videos

### Basic Usage
```bash
# Fetch 50 OHDSI videos
docker-compose exec backend python /app/scripts/ingest/ingest_youtube.py --max-items 50

# Fetch from specific channel
docker-compose exec backend python /app/scripts/ingest/ingest_youtube.py \
    --channel UC3ZkG_OW_A_ChXfHaoVmy_g \
    --max-items 20

# Test with dry-run
docker-compose exec backend python /app/scripts/ingest/ingest_youtube.py \
    --max-items 2 \
    --dry-run
```

### Features
- Searches for OHDSI-related videos
- Extracts video metadata (duration, views)
- Fetches transcripts when available
- Auto-approval threshold: 0.6

### Requirements
- `YOUTUBE_API_KEY` environment variable required

## GitHub Repositories

### Basic Usage
```bash
# Fetch 50 OHDSI repositories
docker-compose exec backend python /app/scripts/ingest/ingest_github.py --max-items 50

# Scan specific organization
docker-compose exec backend python /app/scripts/ingest/ingest_github.py \
    --org OHDSI \
    --max-items 100

# Search for specific query
docker-compose exec backend python /app/scripts/ingest/ingest_github.py \
    --query "OMOP CDM" \
    --max-items 30

# Test with dry-run
docker-compose exec backend python /app/scripts/ingest/ingest_github.py \
    --max-items 2 \
    --dry-run
```

### Features
- Scans OHDSI and OHDSI-Studies organizations
- Searches for OHDSI-related projects
- Extracts repository metrics (stars, forks, activity)
- Auto-approval threshold: 0.65

### Optional
- `GITHUB_TOKEN` environment variable for higher rate limits

## Discourse Forums

### Basic Usage
```bash
# Fetch 50 forum topics
docker-compose exec backend python /app/scripts/ingest/ingest_discourse.py --max-items 50

# Fetch from specific category
docker-compose exec backend python /app/scripts/ingest/ingest_discourse.py \
    --category researchers \
    --max-items 30

# Test with dry-run
docker-compose exec backend python /app/scripts/ingest/ingest_discourse.py \
    --max-items 2 \
    --dry-run
```

### Features
- Fetches from forums.ohdsi.org
- Monitors key categories (researchers, implementers, developers)
- Tracks engagement metrics (views, replies, likes)
- Auto-approval threshold: 0.6

## Wiki/Documentation

### Basic Usage
```bash
# Fetch 50 documentation pages
docker-compose exec backend python /app/scripts/ingest/ingest_wiki.py --max-items 50

# Fetch from specific source
docker-compose exec backend python /app/scripts/ingest/ingest_wiki.py \
    --source "Book of OHDSI" \
    --max-items 20

# Test with dry-run
docker-compose exec backend python /app/scripts/ingest/ingest_wiki.py \
    --max-items 2 \
    --dry-run
```

### Features
- Scrapes multiple documentation sources:
  - OHDSI Wiki
  - Book of OHDSI
  - HADES Documentation
  - OMOP CDM Documentation
  - Atlas Documentation
- Auto-approval threshold: 0.75

## Common Options

All scripts support these options:

| Option | Description | Example |
|--------|-------------|---------||
| `--max-items N` | Maximum items to fetch | `--max-items 100` |
| `--dry-run` | Test without indexing | `--dry-run` |
| `--enable-ai` | Enable GPT-4o-mini enhancement | `--enable-ai` |
| `--save-progress` | Save statistics to file | `--save-progress` |
| `--date-from` | Start date (PubMed only) | `--date-from 2025-01-01` |
| `--date-to` | End date (PubMed only) | `--date-to 2025-08-10` |

## Batch Ingestion Examples

### Daily Ingestion
```bash
# Ingest from all sources
docker-compose exec backend python /app/scripts/ingest/ingest_pubmed.py --max-items 100
docker-compose exec backend python /app/scripts/ingest/ingest_youtube.py --max-items 20
docker-compose exec backend python /app/scripts/ingest/ingest_github.py --max-items 30
docker-compose exec backend python /app/scripts/ingest/ingest_discourse.py --max-items 50
docker-compose exec backend python /app/scripts/ingest/ingest_wiki.py --max-items 10
```

### Test All Sources
```bash
# Quick test with 2 items each
for source in pubmed youtube github discourse wiki; do
    echo "Testing $source..."
    docker-compose exec backend python /app/scripts/ingest/ingest_${source}.py --max-items 2 --dry-run
done
```

### Production Ingestion with AI
```bash
# Full ingestion with AI enhancement
for source in pubmed youtube github discourse wiki; do
    echo "Ingesting from $source..."
    docker-compose exec backend python /app/scripts/ingest/ingest_${source}.py \
        --max-items 50 \
        --enable-ai \
        --save-progress
done
```

## Monitoring

### Check Ingestion Progress
```bash
# View saved progress files
ls -la /app/logs/*_progress.json

# Check specific source progress
docker-compose exec backend cat /app/logs/pubmed_progress.json | python -m json.tool
```

### Verify Indexed Data
```bash
# Check what was indexed
docker-compose exec backend python /app/scripts/check_indexed_data.py

# Check specific document
curl -X GET "localhost:9200/ohdsi_content_v3/_doc/[ID]" | python -m json.tool
```

## Troubleshooting

### Common Issues

1. **API Key Missing**
   ```bash
   export YOUTUBE_API_KEY=your_key
   export GITHUB_TOKEN=your_token  # Optional
   export OPENAI_API_KEY=your_key  # For AI enhancement
   ```

2. **Duplicates**
   - Scripts automatically detect and skip duplicates
   - Check logs for "Duplicate found" messages

3. **Rate Limiting**
   - Reduce `--max-items` value
   - Add API keys for higher limits
   - Space out ingestion runs

4. **Memory Issues**
   - Use smaller batches (e.g., `--max-items 10`)
   - Run sources sequentially, not in parallel

## Scheduling with Cron

```bash
# Add to crontab
crontab -e

# Daily PubMed at 2 AM
0 2 * * * docker-compose -f /path/to/docker-compose.yml exec -T backend python /app/scripts/ingest/ingest_pubmed.py --max-items 100

# Hourly Discourse check
0 * * * * docker-compose -f /path/to/docker-compose.yml exec -T backend python /app/scripts/ingest/ingest_discourse.py --max-items 20

# Weekly GitHub scan on Sundays
0 3 * * 0 docker-compose -f /path/to/docker-compose.yml exec -T backend python /app/scripts/ingest/ingest_github.py --max-items 50
```

## Statistics Output

Each script outputs statistics:
```
pubmed Ingestion Complete:
  Fetched: 100         # Items retrieved from source
  Processed: 95        # Items that passed validation
  Indexed: 90          # Items stored in Elasticsearch
  Duplicates: 5        # Items already in database
  Errors: 0            # Processing errors
  Auto-approved: 72    # Items above threshold
  Sent to review: 18   # Items needing manual review
```