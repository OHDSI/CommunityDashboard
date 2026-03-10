from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
import strawberry
from contextlib import asynccontextmanager
import logging

from .config import settings
from .database import create_indices, Base, engine, SessionLocal
from .api.routes import auth, search, review, user, sso, analytics
from .api.endpoints import pipeline
from .api.graphql.schema import schema
from .models.user import User, UserRole
from .utils.auth import AuthService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_admin_user():
    """Create admin user from ADMIN_EMAIL/ADMIN_PASSWORD env vars if not present."""
    if not settings.admin_email or not settings.admin_password:
        logger.info("ADMIN_EMAIL/ADMIN_PASSWORD not set, skipping admin bootstrap")
        return

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == settings.admin_email).first()
        if existing:
            if existing.role != UserRole.ADMIN:
                existing.role = UserRole.ADMIN
                existing.is_superuser = True
                db.commit()
                logger.info(f"Updated existing user {settings.admin_email} to ADMIN role")
            else:
                logger.info(f"Admin user {settings.admin_email} already exists")
        else:
            admin = User(
                email=settings.admin_email,
                password_hash=AuthService.get_password_hash(settings.admin_password),
                full_name="Admin",
                role=UserRole.ADMIN,
                is_active=True,
                is_superuser=True,
            )
            db.add(admin)
            db.commit()
            logger.info(f"Created admin user: {settings.admin_email}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to bootstrap admin user: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting OHDSI Dashboard API")
    try:
        create_indices()
        logger.info("Elasticsearch indices initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Elasticsearch: {e}")

    try:
        ensure_admin_user()
    except Exception as e:
        logger.error(f"Failed to bootstrap admin user: {e}")

    yield

    # Shutdown
    logger.info("Shutting down OHDSI Dashboard API")

# Create FastAPI app
app = FastAPI(
    title="OHDSI Community Intelligence Platform",
    description="API for OHDSI community content discovery and knowledge management",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ohdsi-dashboard-api",
        "version": "1.0.0"
    }

# Include REST API routes
app.include_router(auth.router, prefix=f"{settings.api_prefix}/auth", tags=["auth"])
app.include_router(sso.router, prefix="/api", tags=["sso"])  # SSO routes at /api/sso/{provider}
app.include_router(search.router, prefix=f"{settings.api_prefix}/search", tags=["search"])
app.include_router(review.router, prefix=f"{settings.api_prefix}/review", tags=["review"])
app.include_router(user.router, prefix=f"{settings.api_prefix}/user", tags=["user"])
app.include_router(pipeline.router, prefix=f"{settings.api_prefix}/pipeline", tags=["pipeline"])
app.include_router(analytics.router)

# Add GraphQL endpoint
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

@app.get("/")
async def root():
    return {
        "message": "OHDSI Community Intelligence Platform API",
        "documentation": "/docs",
        "graphql": "/graphql"
    }