# OHDSI Dashboard Scripts

This directory contains essential scripts for managing the OHDSI Dashboard backend infrastructure, data ingestion, and pipeline operations.

## 📋 Script Categories

### 🏗️ Database & Infrastructure

#### `initialize_database.py`
**Purpose**: Complete database initialization for PostgreSQL and Elasticsearch  
**Usage**: `docker-compose exec backend python /app/scripts/initialize_database.py`  
**Options**: 
- `--force`: Drop existing indices and tables before creating

Sets up:
- PostgreSQL tables and schemas
- Elasticsearch indices with proper mappings for citations
- Initial user accounts
- Required database extensions

#### `init_users.py`
**Purpose**: Create initial user accounts in PostgreSQL  
**Usage**: `docker-compose exec backend python /app/scripts/init_users.py`  

Creates default users with different roles (admin, reviewer, explorer).

### 📊 Data Ingestion

#### `ingest_training_data.py`
**Purpose**: Load ~700 known OHDSI articles from training data  
**Usage**: `docker-compose exec backend python /app/scripts/ingest_training_data.py`  
**Options**:
- `--batch-size`: Number of articles to process at once (default: 20)
- `--skip-ai`: Skip AI enhancement for faster processing

Processes articles through the complete pipeline including:
- PubMed metadata fetching
- Citation enrichment with metadata
- ML classification
- AI enhancement (summaries, embeddings)
- Elasticsearch indexing

#### `reingest_database.py`
**Purpose**: Complete database wipe and reingest with proper citation networks  
**Usage**: `docker-compose exec backend python /app/scripts/reingest_database.py --wipe --confirm`  
**Options**:
- `--bibtex`: Path to BibTeX file (default: training data)
- `--wipe`: Wipe existing database before reingest
- `--confirm`: Required with --wipe to confirm deletion

Complete pipeline for rebuilding the database from scratch with enriched citations.

#### `update_missing_citations.py`
**Purpose**: Update citations for articles already in Elasticsearch  
**Usage**: `docker-compose exec backend python /app/scripts/update_missing_citations.py`  

Fetches and updates citation data for articles missing citation information.

### 🔄 Pipeline Management

#### `manage_pipeline.py`
**Purpose**: Monitor and control the article classification pipeline  
**Usage**: `docker-compose exec backend python /app/scripts/manage_pipeline.py [command]`  
**Commands**:
- `status`: Check pipeline status
- `trigger`: Manually trigger pipeline run
- `history`: View recent pipeline runs

Controls Celery tasks for article fetching and classification.

### 🧪 Testing & Debugging

#### `test_single_article_pipeline.py`
**Purpose**: Test processing of a single article through the complete pipeline  
**Usage**: `docker-compose exec backend python /app/scripts/test_single_article_pipeline.py --pmid 34042737`  

Useful for debugging issues with specific articles.

#### `check_indexed_data.py`
**Purpose**: Verify what data is actually stored in Elasticsearch  
**Usage**: `docker-compose exec backend python /app/scripts/check_indexed_data.py`  

Shows sample documents and field mappings.

#### `verify_citations_enriched.py`
**Purpose**: Verify that documents have enriched citations properly stored  
**Usage**: `docker-compose exec backend python /app/scripts/verify_citations_enriched.py`  

Checks citation format (objects vs IDs) and metadata completeness.

### 🛠️ Utilities

#### `sample_data_generator.py`
**Purpose**: Generate sample data for testing  
**Usage**: `docker-compose exec backend python /app/scripts/sample_data_generator.py`  

Creates test articles with various citation patterns.

#### `kill_ingestion_processes.py` / `kill_ingestion_processes.sh`
**Purpose**: Stop runaway ingestion processes  
**Usage**: `docker-compose exec backend python /app/scripts/kill_ingestion_processes.py`  

Useful when processes get stuck or consume too many resources.

#### `cleanup_obsolete_scripts.py`
**Purpose**: Archive obsolete scripts to keep directory clean  
**Usage**: `python3 cleanup_obsolete_scripts.py --dry-run`  

Maintains a clean scripts directory by archiving outdated files.

### 🚀 Automation

#### `init_db_auto.sh`
**Purpose**: Automated database initialization  
**Usage**: `bash init_db_auto.sh`  

Shell script for automated setup in CI/CD environments.

## 🔧 Common Workflows

### Initial Setup
```bash
# 1. Initialize database
docker-compose exec backend python /app/scripts/initialize_database.py

# 2. Create users
docker-compose exec backend python /app/scripts/init_users.py

# 3. Load training data
docker-compose exec backend python /app/scripts/ingest_training_data.py
```

### Complete Reingest
```bash
# Wipe and rebuild with enriched citations
docker-compose exec backend python /app/scripts/reingest_database.py --wipe --confirm
```

### Debug Citation Issues
```bash
# Check what's indexed
docker-compose exec backend python /app/scripts/check_indexed_data.py

# Verify citation structure
docker-compose exec backend python /app/scripts/verify_citations_enriched.py

# Test single article
docker-compose exec backend python /app/scripts/test_single_article_pipeline.py --pmid 34042737
```

### Pipeline Management
```bash
# Check status
docker-compose exec backend python /app/scripts/manage_pipeline.py status

# Trigger run
docker-compose exec backend python /app/scripts/manage_pipeline.py trigger
```

## 📂 Archived Scripts

Obsolete and debugging scripts are archived in `_archive_*` directories with manifests. These can be recovered if needed but are not part of normal operations.

## ⚠️ Important Notes

1. **Citation Enrichment**: Always use `fetch_metadata=True` when fetching citations to get proper metadata objects
2. **Database Wipes**: Always use `--confirm` flag with wipe operations to prevent accidental data loss
3. **Batch Sizes**: Keep batch sizes reasonable (20-50) to avoid API rate limits
4. **AI Enhancement**: Can be skipped with `--skip-ai` for faster processing during development

## 🔄 Development Guidelines

When adding new scripts:
1. Focus on reusable functionality over one-off debugging
2. Include proper docstrings and usage examples
3. Consider if functionality belongs in existing scripts
4. Run `cleanup_obsolete_scripts.py` periodically to archive old scripts
5. Update this README when adding core functionality scripts