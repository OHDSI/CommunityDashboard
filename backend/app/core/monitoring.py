"""Monitoring and observability configuration."""

import asyncio
import time
from typing import Optional, Dict, Any, Callable
from functools import wraps
from contextlib import contextmanager
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Prometheus metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

active_requests = Gauge(
    'active_requests',
    'Number of active HTTP requests'
)

ml_predictions_total = Counter(
    'ml_predictions_total',
    'Total ML predictions',
    ['model', 'prediction']
)

ml_prediction_duration_seconds = Histogram(
    'ml_prediction_duration_seconds',
    'ML prediction duration in seconds',
    ['model']
)

elasticsearch_queries_total = Counter(
    'elasticsearch_queries_total',
    'Total Elasticsearch queries',
    ['index', 'query_type']
)

elasticsearch_query_duration_seconds = Histogram(
    'elasticsearch_query_duration_seconds',
    'Elasticsearch query duration in seconds',
    ['index', 'query_type']
)

celery_tasks_total = Counter(
    'celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status']
)

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request and collect metrics."""
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Track active requests
        active_requests.inc()
        
        # Start timer
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()
            
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
            
            return response
            
        finally:
            active_requests.dec()

def track_time(metric: Histogram, **labels):
    """Decorator to track function execution time."""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with metric.labels(**labels).time():
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with metric.labels(**labels).time():
                return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

@contextmanager
def track_operation(operation_name: str, **tags):
    """Context manager to track operation timing and success."""
    start_time = time.time()
    success = False
    
    try:
        yield
        success = True
    finally:
        duration = time.time() - start_time
        
        # Log the operation
        from app.core.logging import logger
        logger.info(
            f"Operation completed: {operation_name}",
            extra={
                "operation": operation_name,
                "duration_ms": duration * 1000,
                "success": success,
                **tags
            }
        )

def track_ml_prediction(model_name: str, prediction: str, duration: float):
    """Track ML prediction metrics."""
    ml_predictions_total.labels(
        model=model_name,
        prediction=prediction
    ).inc()
    
    ml_prediction_duration_seconds.labels(
        model=model_name
    ).observe(duration)

def track_elasticsearch_query(index: str, query_type: str, duration: float):
    """Track Elasticsearch query metrics."""
    elasticsearch_queries_total.labels(
        index=index,
        query_type=query_type
    ).inc()
    
    elasticsearch_query_duration_seconds.labels(
        index=index,
        query_type=query_type
    ).observe(duration)

def track_celery_task(task_name: str, status: str):
    """Track Celery task metrics."""
    celery_tasks_total.labels(
        task_name=task_name,
        status=status
    ).inc()

async def metrics_endpoint(request: Request) -> Response:
    """Endpoint to expose Prometheus metrics."""
    metrics = generate_latest()
    return Response(
        content=metrics,
        media_type="text/plain; version=0.0.4"
    )

# Health check utilities
class HealthCheck:
    """Health check for application components."""
    
    @staticmethod
    async def check_database() -> Dict[str, Any]:
        """Check database health."""
        from app.database import engine
        
        try:
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            return {"status": "unhealthy", "database": str(e)}
    
    @staticmethod
    async def check_elasticsearch() -> Dict[str, Any]:
        """Check Elasticsearch health."""
        from app.database import es_client
        
        try:
            health = es_client.cluster.health()
            return {
                "status": "healthy" if health["status"] in ["green", "yellow"] else "unhealthy",
                "elasticsearch": health["status"]
            }
        except Exception as e:
            return {"status": "unhealthy", "elasticsearch": str(e)}
    
    @staticmethod
    async def check_redis() -> Dict[str, Any]:
        """Check Redis health."""
        from app.database import redis_client
        
        try:
            redis_client.ping()
            return {"status": "healthy", "redis": "connected"}
        except Exception as e:
            return {"status": "unhealthy", "redis": str(e)}
    
    @staticmethod
    async def get_health_status() -> Dict[str, Any]:
        """Get overall health status."""
        results = {
            "status": "healthy",
            "checks": {}
        }
        
        # Check all components
        for check_name, check_func in [
            ("database", HealthCheck.check_database),
            ("elasticsearch", HealthCheck.check_elasticsearch),
            ("redis", HealthCheck.check_redis)
        ]:
            check_result = await check_func()
            results["checks"][check_name] = check_result
            
            if check_result["status"] == "unhealthy":
                results["status"] = "unhealthy"
        
        return results