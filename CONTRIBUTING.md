# Contributing to the OHDSI Community Intelligence Platform

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend development outside Docker)
- Python 3.11+ (for backend development outside Docker)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/OHDSI/ohdsi-dashboard.git
cd ohdsi-dashboard

# Copy environment template
cp .env.example .env
# Edit .env with your configuration (see comments in .env.example)

# Start all services
docker compose up --build
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- GraphQL Playground: http://localhost:8000/graphql

### Service Architecture

```
Frontend (Next.js) → GraphQL API (FastAPI/Strawberry) → Elasticsearch
                                                       → PostgreSQL
                                                       → Redis/Celery
```

## How to Contribute

### Reporting Issues

- Use GitHub Issues to report bugs or suggest features
- Include steps to reproduce for bug reports
- Check existing issues before creating a new one

### Pull Requests

1. Fork the repository
2. Create a feature branch from `main`: `git checkout -b feature/your-feature`
3. Make your changes
4. Ensure the application builds: `docker compose build`
5. Test your changes locally
6. Submit a pull request with a clear description

### Coding Standards

**Backend (Python)**
- Follow PEP 8
- Use type hints
- Write docstrings for public functions

**Frontend (TypeScript/React)**
- Use TypeScript strict mode
- Follow the existing component patterns
- Use the design token system in `frontend/lib/design-tokens/`

### Commit Messages

Use clear, descriptive commit messages:
- `fix: resolve search pagination bug`
- `feat: add article export functionality`
- `docs: update API documentation`

## Project Structure

```
ohdsi-dashboard/
├── backend/                 # FastAPI backend
│   ├── app/                 # Application code
│   │   ├── api/graphql/     # GraphQL schema and resolvers
│   │   ├── models/          # SQLAlchemy models
│   │   ├── services/        # Business logic
│   │   └── utils/           # Utilities (auth, etc.)
│   ├── jobs/                # Background jobs and ML pipeline
│   └── scripts/             # Operational scripts
├── frontend/                # Next.js frontend
│   ├── app/                 # Pages (App Router)
│   ├── components/          # React components
│   └── lib/                 # Utilities, API clients, design tokens
├── scripts/                 # Database initialization
└── docker-compose.yml       # Service orchestration
```

## Questions?

Open a GitHub Issue or reach out to the OHDSI community at https://forums.ohdsi.org.
