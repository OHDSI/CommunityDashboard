# OHDSI Community Intelligence Platform

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

An intelligent content discovery and classification platform for the [OHDSI](https://ohdsi.org/) (Observational Health Data Sciences and Informatics) community. This system automatically fetches, classifies, and manages research articles and community content, providing a comprehensive pipeline for content curation.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/OHDSI/ohdsi-dashboard.git
cd ohdsi-dashboard

# Copy and configure environment
cp .env.example .env
# Edit .env with your configuration (API keys, admin credentials, etc.)

# Start the platform
docker compose up --build
```

Visit http://localhost:3000 to access the application.

## Features

### Automated Content Pipeline
- **Daily PubMed fetching** using learned and hand-crafted OHDSI-specific queries
- **ML classification** with a RandomForest model (F1=0.96, AUC=0.99) trained on 1,195 labeled articles
- **Calibrated thresholds** for auto-approval, priority review, and auto-rejection
- **Citation network analysis** for enriched feature engineering
- **Scheduled execution** via Celery Beat (daily at 2 AM UTC)

### Multi-Source Content
- **PubMed articles** with full metadata, citations, and MeSH terms
- **YouTube videos** with transcript extraction from OHDSI channels
- **GitHub repositories** from the OHDSI organization

### Search and Discovery
- Full-text search across all content types with faceted filtering

## Architecture

```
Frontend (Next.js 14)
  │
  ├── Search (public)
  ├── Review Queue (authenticated)
  ├── Analytics (authenticated)
  └── Admin (admin only)
  │
GraphQL API (FastAPI + Strawberry)
  │
  ├── PostgreSQL (users, auth, preferences)
  ├── Elasticsearch (content index, review queue)
  ├── Redis (caching, task broker)
  └── Celery (background jobs, ML pipeline)
```

## Configuration

All configuration is via environment variables. See [`.env.example`](.env.example) for the complete list.

Key variables:
| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | JWT signing key |
| `ADMIN_EMAIL` | Yes | Bootstrap admin account email |
| `ADMIN_PASSWORD` | Yes | Bootstrap admin account password |
| `NCBI_ENTREZ_EMAIL` | Yes | For PubMed API access |
| `OPENAI_API_KEY` | No | For AI-enhanced features |
| `NCBI_ENTREZ_API_KEY` | No | Higher PubMed rate limits |

## Development

```bash
# View service logs
docker compose logs -f backend
docker compose logs -f frontend

# Access backend shell
docker compose exec backend bash

# Access database
docker compose exec postgresql psql -U ohdsi_user -d ohdsi_dashboard

# Run ML classifier training
docker compose exec backend python -c "
from jobs.article_classifier.wrapper import ArticleClassifierWrapper
w = ArticleClassifierWrapper()
w.train_classifier(force_retrain=True)
"
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and contribution guidelines.

## ML Classification System

The article classifier uses 125 engineered features:
- **19 intrinsic features**: abstract length, author count, keyword mentions, etc.
- **6 network features**: topic author overlap, citation graph analysis, co-authorship
- **100 TF-IDF features**: abstract text vectorization

Evaluation (5-fold cross-validation with hard negatives):
- F1 = 0.963, AUC = 0.990
- Auto-approve threshold: 0.64 (precision 0.98)
- Auto-reject threshold: 0.07 (NPV 1.00)
- ~17% of articles routed to human review

## Security

See [SECURITY.md](SECURITY.md) for security policy and vulnerability reporting.

## License

This project is licensed under the Apache License 2.0 — see [LICENSE](LICENSE) for details.

Part of the [OHDSI](https://ohdsi.org/) community initiative for advancing observational health data sciences and informatics.
