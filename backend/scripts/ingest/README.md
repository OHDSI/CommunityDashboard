# Independent Ingestion Scripts

Modular ingestion scripts for fetching content from different sources into the OHDSI Dashboard.

## Overview

Each source has its own independent ingestion script that can be run separately. All scripts inherit from a common base class (`BaseIngestion`) that provides the standard pipeline:

1. **Fetch** - Get content from the source
2. **Normalize** - Convert to unified schema
3. **Deduplicate** - Check for existing content
4. **Classify** - ML scoring for relevance
5. **Enhance** - Optional AI enrichment
6. **Route** - Send to approval or review queue
7. **Index** - Store in Elasticsearch

## Available Scripts

### PubMed Articles (`ingest_pubmed.py`)

Fetches scientific articles from PubMed with enriched citations.

```bash
# Fetch 100 articles from last 30 days
docker-compose exec backend python /app/scripts/ingest/ingest_pubmed.py --max-items 100

# Fetch articles from specific date range
docker-compose exec backend python /app/scripts/ingest/ingest_pubmed.py \
    --max-items 50 \
    --date-from 2025-01-01 \
    --date-to 2025-08-10

# With AI enhancement
docker-compose exec backend python /app/scripts/ingest/ingest_pubmed.py \
    --max-items 50 \
    --enable-ai
```

**Features:**
- OHDSI-specific search queries
- Enriched citation metadata (title, year, journal, authors)
- Citation network building
- Automatic quality scoring

### YouTube Videos (`ingest_youtube.py`)

Fetches OHDSI-related videos from YouTube channels and searches.

```bash
# Fetch 50 videos from all OHDSI sources
docker-compose exec backend python /app/scripts/ingest/ingest_youtube.py --max-items 50

# Fetch from specific channel
docker-compose exec backend python /app/scripts/ingest/ingest_youtube.py \
    --channel UC3ZkG_OW_A_ChXfHaoVmy_g \
    --max-items 20

# Fetch from specific playlist
docker-compose exec backend python /app/scripts/ingest/ingest_youtube.py \
    --playlist PLpzbqK7kvfeXOyX1jF7Nr3z8tbtJSRdoZ \
    --max-items 30
```

**Features:**
- Monitors official OHDSI channels
- Searches for OHDSI-related content
- Extracts video metadata (duration, views, likes)
- Transcript fetching (when available)

### GitHub Repositories (`ingest_github.py`)

Scans GitHub for OHDSI repositories and projects.

```bash
# Fetch 50 repositories
docker-compose exec backend python /app/scripts/ingest/ingest_github.py --max-items 50

# Scan specific organization
docker-compose exec backend python /app/scripts/ingest/ingest_github.py \
    --org OHDSI \
    --max-items 100

# Search for specific query
docker-compose exec backend python /app/scripts/ingest/ingest_github.py \
    --query "OMOP CDM" \
    --max-items 30
```

**Features:**
- Scans OHDSI organizations
- Searches for OHDSI-related projects
- README content extraction
- Repository quality metrics (stars, forks, activity)

### Discourse Forums (`ingest_discourse.py`)

Fetches discussions from forums.ohdsi.org.

```bash
# Fetch 50 latest topics
docker-compose exec backend python /app/scripts/ingest/ingest_discourse.py --max-items 50

# Fetch from specific category
docker-compose exec backend python /app/scripts/ingest/ingest_discourse.py \
    --category researchers \
    --max-items 30
```

**Features:**
- Monitors key forum categories
- Fetches full topic discussions
- Engagement metrics (views, replies, likes)
- Solution tracking

### Wiki/Documentation (`ingest_wiki.py`)

Scrapes OHDSI documentation from various sources.

```bash
# Fetch 50 documentation pages
docker-compose exec backend python /app/scripts/ingest/ingest_wiki.py --max-items 50

# Fetch from specific source
docker-compose exec backend python /app/scripts/ingest/ingest_wiki.py \
    --source "Book of OHDSI" \
    --max-items 20
```

**Features:**
- Multiple documentation sources (Wiki, Book of OHDSI, HADES docs)
- Structured content extraction
- Documentation type classification
- Complexity level detection

## Common Options

All scripts support these common options:

- `--max-items N` - Maximum number of items to fetch (default: 50)
- `--enable-ai` - Enable AI enhancement with GPT-4o-mini
- `--dry-run` - Test run without indexing to Elasticsearch
- `--save-progress` - Save ingestion statistics to file
- `--date-from YYYY-MM-DD` - Start date for fetching (where applicable)
- `--date-to YYYY-MM-DD` - End date for fetching (where applicable)

## Configuration

Each script has configurable thresholds:

- **auto_approve_threshold** - Score above this is auto-approved (0.0-1.0)
- **priority_threshold** - Score above this is high-priority review (0.0-1.0)

Default thresholds by content type:
- PubMed: 0.7 (auto-approve), 0.5 (priority)
- YouTube: 0.6 (auto-approve), 0.4 (priority)
- GitHub: 0.65 (auto-approve), 0.45 (priority)
- Discourse: 0.6 (auto-approve), 0.4 (priority)
- Wiki: 0.75 (auto-approve), 0.5 (priority)

## Pipeline Flow

Each script follows this processing pipeline:

```
1. Fetch Content
   ├── Source-specific API calls
   └── Rate limiting and retries

2. Validate Content
   ├── Check required fields
   └── Basic relevance check

3. Process Item
   ├── Normalize to unified schema
   ├── Check for duplicates
   ├── Calculate quality score
   ├── ML classification
   ├── AI enhancement (optional)
   └── Route to queue

4. Index to Elasticsearch
   ├── Content index (approved)
   └── Review index (pending)
```

## Monitoring

Each script outputs statistics:

```
PubMed Ingestion Complete:
  Fetched: 100
  Processed: 95
  Indexed: 90
  Duplicates: 5
  Errors: 0
  Auto-approved: 72
  Sent to review: 18
```

Progress files are saved to `/app/logs/[source]_progress.json` when using `--save-progress`.

## Scheduling

These scripts can be scheduled with cron or Celery:

### Cron Example

```bash
# Daily PubMed ingestion at 2 AM
0 2 * * * docker-compose exec -T backend python /app/scripts/ingest/ingest_pubmed.py --max-items 100

# Weekly GitHub scan on Sundays
0 3 * * 0 docker-compose exec -T backend python /app/scripts/ingest/ingest_github.py --max-items 50

# Hourly Discourse check
0 * * * * docker-compose exec -T backend python /app/scripts/ingest/ingest_discourse.py --max-items 20
```

### Celery Task Integration

Create Celery tasks that call these scripts:

```python
@shared_task
def ingest_pubmed_task(max_items=50):
    from scripts.ingest.ingest_pubmed import PubMedIngestion
    ingestion = PubMedIngestion()
    return ingestion.ingest(max_items=max_items)

@shared_task
def ingest_all_sources():
    results = {}
    results['pubmed'] = ingest_pubmed_task.delay(100).get()
    results['youtube'] = ingest_youtube_task.delay(20).get()
    results['github'] = ingest_github_task.delay(30).get()
    results['discourse'] = ingest_discourse_task.delay(50).get()
    results['wiki'] = ingest_wiki_task.delay(10).get()
    return results
```

## Troubleshooting

### API Keys

Some sources require API keys:

```bash
# YouTube (required)
export YOUTUBE_API_KEY=your_key

# GitHub (optional, for higher rate limits)
export GITHUB_TOKEN=your_token

# OpenAI (for AI enhancement)
export OPENAI_API_KEY=your_key
```

### Rate Limiting

All scripts implement rate limiting. If you hit limits:
- Reduce `--max-items`
- Add delays between runs
- Use API keys for higher limits

### Duplicates

Duplicates are automatically detected using:
- Content fingerprinting
- Title/URL matching
- Similarity scoring

Duplicates are skipped and counted in statistics.

### Memory Issues

For large ingestions:
- Process in smaller batches
- Use `--max-items` to limit per run
- Monitor Docker container memory

## Development

### Adding a New Source

1. Create new script `ingest_[source].py`
2. Inherit from `BaseIngestion`
3. Implement required methods:
   - `fetch_content()` - Get data from source
   - `validate_content()` - Check required fields
   - `process_item()` - Add source-specific processing

### Testing

Test individual scripts:

```bash
# Dry run to test without indexing
python /app/scripts/ingest/ingest_pubmed.py --max-items 5 --dry-run

# Test with small batch
python /app/scripts/ingest/ingest_youtube.py --max-items 2
```

## Related Scripts

- `/app/scripts/initialize_database.py` - Set up Elasticsearch indices
- `/app/scripts/check_indexed_data.py` - Verify indexed content
- `/app/scripts/manage_pipeline.py` - Monitor ingestion pipeline
- `/app/jobs/pipeline_orchestrator.py` - Original multi-source orchestrator