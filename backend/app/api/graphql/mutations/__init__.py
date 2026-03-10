"""
GraphQL Mutation definitions for the OHDSI Community Intelligence Platform.

All mutation resolvers are defined in domain-specific modules and merged
into a single Mutation class here, since Strawberry requires a single
Mutation type for the schema.
"""
import strawberry
from strawberry.types import Info
from typing import Optional, List

from ..types import (
    AuthPayload, User, PredictionResult, PubMedPrediction,
)

from .auth import resolve_register, resolve_login
from .review import (
    resolve_approve_content,
    resolve_reject_content,
    resolve_move_to_pending,
    resolve_change_content_status,
    resolve_bookmark,
    resolve_save_search,
)
from .user import (
    resolve_create_user,
    resolve_update_user_role,
    resolve_deactivate_user,
)
from .prediction import (
    resolve_predict_text,
    resolve_predict_pubmed,
    resolve_submit_prediction,
    resolve_trigger_article_pipeline,
)


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def register(
        self,
        email: str,
        password: str,
        full_name: str,
        organization: Optional[str] = None
    ) -> AuthPayload:
        """Register new user"""
        return await resolve_register(email, password, full_name, organization)

    @strawberry.mutation
    async def login(self, email: str, password: str) -> AuthPayload:
        """Login user"""
        return await resolve_login(email, password)

    @strawberry.mutation
    async def approve_content(
        self,
        info: Info,
        id: str,
        categories: List[str]
    ) -> bool:
        """Approve content (requires reviewer role)"""
        return await resolve_approve_content(info, id, categories)

    @strawberry.mutation
    async def reject_content(
        self,
        info: Info,
        id: str,
        reason: str
    ) -> bool:
        """Reject content (requires reviewer role)"""
        return await resolve_reject_content(info, id, reason)

    @strawberry.mutation
    async def move_to_pending(
        self,
        info: Info,
        id: str,
        notes: Optional[str] = None
    ) -> bool:
        """Move an approved or rejected item back to pending status"""
        return await resolve_move_to_pending(info, id, notes)

    @strawberry.mutation
    async def change_content_status(
        self,
        info: Info,
        id: str,
        new_status: str,
        categories: Optional[List[str]] = None
    ) -> bool:
        """Change content status (approved -> pending for re-review)"""
        return await resolve_change_content_status(info, id, new_status, categories)

    @strawberry.mutation
    async def bookmark(
        self,
        info: Info,
        content_id: str
    ) -> bool:
        """Bookmark content"""
        return resolve_bookmark(info, content_id)

    @strawberry.mutation
    async def save_search(
        self,
        info: Info,
        query: str,
        name: str
    ) -> bool:
        """Save search query"""
        return resolve_save_search(info, query, name)

    @strawberry.mutation
    async def create_user(
        self,
        info: Info,
        email: str,
        password: str,
        full_name: str,
        role: str = "reviewer",
    ) -> User:
        """Create a new user (requires admin role)"""
        return resolve_create_user(info, email, password, full_name, role)

    @strawberry.mutation
    async def update_user_role(
        self,
        info: Info,
        user_id: str,
        role: str,
    ) -> bool:
        """Update a user's role (requires admin role)"""
        return resolve_update_user_role(info, user_id, role)

    @strawberry.mutation
    async def deactivate_user(
        self,
        info: Info,
        user_id: str,
    ) -> bool:
        """Deactivate a user (requires admin role)"""
        return resolve_deactivate_user(info, user_id)

    @strawberry.mutation
    async def predict_text(
        self,
        title: str,
        abstract: str,
        authors: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None
    ) -> PredictionResult:
        """Predict OHDSI relevance for submitted text"""
        return resolve_predict_text(title, abstract, authors, keywords)

    @strawberry.mutation
    async def predict_pubmed(self, pmid: str) -> PubMedPrediction:
        """Predict OHDSI relevance for a PubMed article"""
        return resolve_predict_pubmed(pmid)

    @strawberry.mutation
    async def submit_prediction(
        self,
        title: str,
        abstract: str,
        confidence_score: float,
        predicted_categories: List[str],
        authors: Optional[List[str]] = None
    ) -> bool:
        """Submit predicted content for review or auto-approval"""
        return resolve_submit_prediction(title, abstract, confidence_score, predicted_categories, authors)

    @strawberry.mutation
    async def trigger_article_pipeline(self, info: Info) -> bool:
        """Manually trigger the article classification pipeline (requires admin)"""
        return resolve_trigger_article_pipeline(info)
