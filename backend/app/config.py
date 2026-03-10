from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # PostgreSQL settings
    POSTGRES_HOST: str = "postgresql"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "ohdsi_user"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "ohdsi_dashboard"
    
    # Elasticsearch settings
    ELASTICSEARCH_HOST: str = "elasticsearch"
    ELASTICSEARCH_PORT: int = 9200
    elasticsearch_timeout: int = 30
    elasticsearch_password: Optional[str] = None
    
    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    redis_url: str = "redis://redis:6379"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    refresh_token_expire_days: int = 7

    # Admin bootstrap
    admin_email: Optional[str] = os.getenv("ADMIN_EMAIL")
    admin_password: Optional[str] = os.getenv("ADMIN_PASSWORD")
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]
    
    # SSO Configuration
    base_url: str = os.getenv("BASE_URL", "http://localhost:8000")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Google OAuth
    google_client_id: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    
    # GitHub OAuth
    github_client_id: Optional[str] = os.getenv("GITHUB_CLIENT_ID")
    github_client_secret: Optional[str] = os.getenv("GITHUB_CLIENT_SECRET")
    
    # Microsoft Azure AD
    azure_client_id: Optional[str] = os.getenv("AZURE_CLIENT_ID")
    azure_client_secret: Optional[str] = os.getenv("AZURE_CLIENT_SECRET")
    azure_tenant_id: Optional[str] = os.getenv("AZURE_TENANT_ID")
    
    # ORCID OAuth (for researchers)
    orcid_client_id: Optional[str] = os.getenv("ORCID_CLIENT_ID")
    orcid_client_secret: Optional[str] = os.getenv("ORCID_CLIENT_SECRET")

    # OpenAI API (for analytics LLM features)
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def elasticsearch_url(self) -> str:
        return f"http://{self.ELASTICSEARCH_HOST}:{self.ELASTICSEARCH_PORT}"
    
    # API
    api_prefix: str = "/api/v1"
    
    # Elasticsearch indices
    content_index: str = "ohdsi_content_v3"
    review_index: str = "ohdsi_review_queue_v3"
    activity_index: str = "user_activity"
    
    # ArticleClassifier
    classifier_threshold: float = 0.7
    classifier_batch_size: int = 100
    
    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100
    
    class Config:
        case_sensitive = False

settings = Settings()