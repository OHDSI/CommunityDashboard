"""
OHDSI Community Intelligence Platform - GraphQL Schema

This module creates the Strawberry GraphQL schema by composing
Query and Mutation classes from their respective sub-modules.

Note: Strawberry automatically converts snake_case Python fields
to camelCase in GraphQL.
"""
import strawberry
from .queries import Query
from .mutations import Mutation

schema = strawberry.Schema(query=Query, mutation=Mutation)
