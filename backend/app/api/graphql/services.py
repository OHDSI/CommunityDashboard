"""
Shared service instances for GraphQL resolvers.

Centralizes service initialization so all query/mutation modules
can import from a single location.
"""
from ...services.search_service import SearchService
from ...services.review_service import ReviewService
from ...database import es_client, redis_client

# Initialize services
search_service = SearchService(es_client, redis_client)
review_service = ReviewService(es_client)

# These services are expected to be available at module level.
# They are referenced in queries/mutations but were never explicitly
# imported in the original monolithic schema. We keep the same pattern
# here: they must be importable from the app context at runtime.
try:
    from ...services.prediction_service import PredictionService
    prediction_service = PredictionService(es_client)
except ImportError:
    prediction_service = None

try:
    from ...services.dashboard_service import DashboardService
    dashboard_service = DashboardService(es_client, redis_client)
except ImportError:
    dashboard_service = None

try:
    from ...services.citation_service import CitationService
    citation_service = CitationService(es_client)
except ImportError:
    citation_service = None

try:
    from ...services.landscape_service import LandscapeService
    landscape_service = LandscapeService(es_client)
except ImportError:
    landscape_service = None
