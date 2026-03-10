"""SSO Service for handling OAuth2/OIDC authentication."""

import secrets
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from authlib.integrations.starlette_client import OAuth, OAuthError
from authlib.jose import jwt
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..config import settings
from ..models import User, UserRole
from ..utils.auth import auth_service

logger = logging.getLogger(__name__)


class SSOService:
    """Service for handling SSO authentication with multiple providers."""
    
    def __init__(self):
        """Initialize OAuth client and register providers."""
        self.oauth = OAuth()
        self._register_providers()
        self._state_store = {}  # In production, use Redis for state storage
    
    def _register_providers(self):
        """Register OAuth providers based on configuration."""
        
        # Google OAuth2
        if settings.google_client_id and settings.google_client_secret:
            self.oauth.register(
                name='google',
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
                client_kwargs={
                    'scope': 'openid email profile'
                }
            )
            logger.info("Google OAuth provider registered")
        
        # GitHub OAuth2
        if settings.github_client_id and settings.github_client_secret:
            self.oauth.register(
                name='github',
                client_id=settings.github_client_id,
                client_secret=settings.github_client_secret,
                access_token_url='https://github.com/login/oauth/access_token',
                access_token_params=None,
                authorize_url='https://github.com/login/oauth/authorize',
                authorize_params=None,
                api_base_url='https://api.github.com/',
                client_kwargs={'scope': 'user:email'},
            )
            logger.info("GitHub OAuth provider registered")
        
        # Microsoft Azure AD
        if settings.azure_client_id and settings.azure_client_secret and settings.azure_tenant_id:
            self.oauth.register(
                name='azure',
                client_id=settings.azure_client_id,
                client_secret=settings.azure_client_secret,
                server_metadata_url=f'https://login.microsoftonline.com/{settings.azure_tenant_id}/v2.0/.well-known/openid-configuration',
                client_kwargs={
                    'scope': 'openid email profile'
                }
            )
            logger.info("Azure AD OAuth provider registered")
        
        # ORCID OAuth2 (for researchers)
        if settings.orcid_client_id and settings.orcid_client_secret:
            self.oauth.register(
                name='orcid',
                client_id=settings.orcid_client_id,
                client_secret=settings.orcid_client_secret,
                access_token_url='https://orcid.org/oauth/token',
                authorize_url='https://orcid.org/oauth/authorize',
                api_base_url='https://pub.orcid.org/v3.0/',
                client_kwargs={'scope': '/authenticate'},
            )
            logger.info("ORCID OAuth provider registered")
    
    def generate_state(self) -> str:
        """Generate a secure random state parameter."""
        state = secrets.token_urlsafe(32)
        # Store state with timestamp for cleanup (expires in 10 minutes)
        self._state_store[state] = datetime.utcnow()
        return state
    
    def verify_state(self, state: str) -> bool:
        """Verify state parameter to prevent CSRF attacks."""
        if state not in self._state_store:
            return False
        
        # Check if state is not expired (10 minutes)
        created_at = self._state_store[state]
        if (datetime.utcnow() - created_at).seconds > 600:
            del self._state_store[state]
            return False
        
        # State is valid, remove it (one-time use)
        del self._state_store[state]
        return True
    
    def get_provider(self, provider_name: str):
        """Get OAuth client for specified provider."""
        if not hasattr(self.oauth, provider_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Provider {provider_name} is not configured"
            )
        return getattr(self.oauth, provider_name)
    
    async def get_user_info(self, provider_name: str, token: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user information from OAuth token based on provider."""
        
        user_info = {
            'provider': provider_name,
            'email': None,
            'full_name': None,
            'email_verified': False,
            'provider_id': None
        }
        
        if provider_name == 'google':
            # Google provides user info in ID token
            if 'id_token' in token:
                claims = jwt.decode(token['id_token'], options={"verify_signature": False})
                user_info['email'] = claims.get('email')
                user_info['full_name'] = claims.get('name')
                user_info['email_verified'] = claims.get('email_verified', False)
                user_info['provider_id'] = claims.get('sub')
        
        elif provider_name == 'github':
            # GitHub requires separate API call for user info
            provider = self.get_provider(provider_name)
            resp = await provider.get('user', token=token)
            resp.raise_for_status()
            data = resp.json()
            
            user_info['email'] = data.get('email')
            user_info['full_name'] = data.get('name')
            user_info['provider_id'] = str(data.get('id'))
            user_info['email_verified'] = True  # GitHub verifies emails
            
            # Get primary email if not public
            if not user_info['email']:
                email_resp = await provider.get('user/emails', token=token)
                email_resp.raise_for_status()
                emails = email_resp.json()
                for email in emails:
                    if email.get('primary') and email.get('verified'):
                        user_info['email'] = email.get('email')
                        break
        
        elif provider_name == 'azure':
            # Azure AD provides user info in ID token
            if 'id_token' in token:
                claims = jwt.decode(token['id_token'], options={"verify_signature": False})
                user_info['email'] = claims.get('email') or claims.get('preferred_username')
                user_info['full_name'] = claims.get('name')
                user_info['email_verified'] = True  # Azure AD verifies emails
                user_info['provider_id'] = claims.get('oid') or claims.get('sub')
        
        elif provider_name == 'orcid':
            # ORCID provides limited info, mainly the ORCID iD
            if 'orcid' in token:
                user_info['provider_id'] = token['orcid']
                user_info['email_verified'] = True
                # ORCID doesn't provide email in basic auth scope
                # Would need /read-limited scope for that
        
        return user_info
    
    async def get_or_create_user(self, db: Session, user_info: Dict[str, Any]) -> User:
        """Get existing user or create new one from SSO info."""
        
        # First, try to find user by SSO provider and ID
        if user_info['provider_id']:
            user = db.query(User).filter(
                User.sso_provider == user_info['provider'],
                User.sso_id == user_info['provider_id']
            ).first()
            
            if user:
                # Update last login
                user.last_login = datetime.utcnow()
                db.commit()
                return user
        
        # Try to find user by email (for account linking)
        if user_info['email']:
            user = db.query(User).filter(User.email == user_info['email']).first()
            
            if user:
                # Link SSO account to existing user
                if not user.sso_provider:
                    user.sso_provider = user_info['provider']
                    user.sso_id = user_info['provider_id']
                    user.sso_email_verified = user_info['email_verified']
                    user.last_login = datetime.utcnow()
                    db.commit()
                    logger.info(f"Linked {user_info['provider']} account to existing user {user.email}")
                return user
        
        # Create new user
        if not user_info['email']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required for account creation"
            )
        
        # For SSO users, we don't have a password, so generate a random one
        # They won't use it since they'll always login via SSO
        random_password = secrets.token_urlsafe(32)
        
        user = User(
            email=user_info['email'],
            password_hash=auth_service.get_password_hash(random_password),
            full_name=user_info['full_name'],
            sso_provider=user_info['provider'],
            sso_id=user_info['provider_id'],
            sso_email_verified=user_info['email_verified'],
            role=self._determine_initial_role(user_info),
            is_active=True,
            last_login=datetime.utcnow()
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"Created new user {user.email} via {user_info['provider']} SSO")
        return user
    
    def _determine_initial_role(self, user_info: Dict[str, Any]) -> UserRole:
        """Determine initial user role based on SSO provider and email domain."""
        
        # Researchers with ORCID get researcher role
        if user_info['provider'] == 'orcid':
            return UserRole.RESEARCHER
        
        # Check email domain for known institutions
        email = user_info.get('email', '')
        if email:
            domain = email.split('@')[-1].lower()
            
            # Academic institutions
            if domain.endswith('.edu'):
                return UserRole.RESEARCHER
            
            # Healthcare organizations
            healthcare_domains = ['mayo.edu', 'partners.org', 'kaiserpermanente.org']
            if any(domain.endswith(d) for d in healthcare_domains):
                return UserRole.IMPLEMENTER
            
            # Known OHDSI contributors
            ohdsi_domains = ['ohdsi.org', 'odysseusinc.com']
            if any(domain.endswith(d) for d in ohdsi_domains):
                return UserRole.CONTRIBUTOR
        
        # Default role for new SSO users
        return UserRole.LEARNER
    
    def create_jwt_token(self, user: User) -> str:
        """Create JWT token for authenticated user."""
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value
        }
        return auth_service.create_access_token(data=token_data)


# Create singleton instance
sso_service = SSOService()