# OHDSI Multi-Source Content Pipeline

Fetches, classifies, and indexes OHDSI-related content from multiple sources.

## Architecture

```
Content Sources    →    Shared Infrastructure    →    Elasticsearch
─────────────────       ──────────────────────       ──────────────
PubMed articles         ContentNormalizer             ohdsi_content_v3
YouTube videos          UnifiedMLClassifier           ohdsi_review_queue_v3
GitHub repositories     AIEnhancer (GPT-4o-mini)
Discourse forums        QueueManager
OHDSI Wiki/Docs         Deduplicator
```

**PubMed articles** follow a specialized path through the `article_classifier/` module with a RandomForest model (F1=0.963, AUC=0.990) and calibrated auto-approve/reject thresholds. All other sources go through `pipeline_orchestrator.py` and the `shared/` utilities.

## Directory Structure

```
jobs/
├── pipeline_orchestrator.py     # Main coordinator for all content sources
├── article_classifier/          # PubMed-specific ML classification
│   ├── wrapper.py               # Celery task entry point (daily fetch + routing)
│   ├── enhanced_classifier_v2.py # RandomForest/XGBoost classifier (125 features)
│   ├── feature_transformers.py  # Feature engineering (single source of truth)
│   ├── retriever.py             # PubMed API integration + citation enrichment
│   ├── pmc_enhancer.py          # PMC author affiliation/ORCID enrichment
│   ├── query_learner/           # Learns optimized PubMed search queries
│   ├── data/                    # Training data, queries, author configs
│   └── models/                  # Trained model files (.pkl)
├── youtube_fetcher/             # YouTube video + transcript fetching
├── github_scanner/              # GitHub org/repo scanning + README analysis
├── discourse_fetcher/           # OHDSI forum topic fetching
├── wiki_scraper/                # Wiki and Book of OHDSI scraping
├── shared/                      # Shared infrastructure
│   ├── base_fetcher.py          # Abstract base with rate limiting + retry
│   ├── content_normalizer.py    # Unified schema normalization
│   ├── ml_classifier.py         # Adapts article classifier for all content
│   ├── queue_manager.py         # Auto-approve / review queue routing
│   ├── ai_enhancer.py           # GPT-4o-mini enrichment + embeddings
│   └── utils/                   # Rate limiter, deduplicator, quality scorer
└── requirements.txt             # Pipeline dependencies
```

## Quick Start

```bash
# Run daily content fetch (all sources)
docker compose exec backend python -c "
from jobs.pipeline_orchestrator import ContentPipelineOrchestrator
o = ContentPipelineOrchestrator()
o.run_daily_fetch()
"

# Run PubMed article classification only
docker compose exec backend python -c "
from jobs.article_classifier.wrapper import ArticleClassifierWrapper
w = ArticleClassifierWrapper()
w.run_daily_fetch()
"

# Retrain ML classifier
docker compose exec backend python -c "
from jobs.article_classifier.wrapper import ArticleClassifierWrapper
w = ArticleClassifierWrapper()
w.train_classifier(force_retrain=True)
"
```

In production, these tasks run automatically via Celery Beat (daily at 1-2 AM UTC).

## Configuration

See `CLAUDE.md` in this directory for environment variables, calibrated thresholds, and detailed technical documentation.

## Adding a New Content Source

1. Create a fetcher directory (e.g., `jobs/new_source/`)
2. Subclass `BaseFetcher` from `shared/base_fetcher.py` and implement `_fetch_single()`
3. Add a normalizer in `shared/content_normalizer.py` for the unified schema
4. Register the fetcher in `pipeline_orchestrator.py`
5. Add any required API keys to the environment
