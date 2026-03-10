"""SSO authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuthError
import logging
from typing import Optional

from ...database import get_db
from ...config import settings
from ...services.sso_service import sso_service
from ...schemas import Token, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sso", tags=["sso"])


@router.get("/{provider}/login")
async def sso_login(request: Request, provider: str):
    """Initiate SSO login flow for specified provider."""
    
    try:
        # Get OAuth client for provider
        oauth_client = sso_service.get_provider(provider)
        
        # Generate state for CSRF protection
        state = sso_service.generate_state()
        
        # Build redirect URI
        redirect_uri = f"{settings.base_url}/api/sso/{provider}/callback"
        
        # Create authorization URL
        return await oauth_client.authorize_redirect(
            request,
            redirect_uri,
            state=state
        )
        
    except Exception as e:
        logger.error(f"SSO login error for {provider}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to initiate {provider} login"
        )


@router.get("/{provider}/callback")
async def sso_callback(
    request: Request,
    provider: str,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Handle OAuth callback from provider."""
    
    # Check for OAuth errors
    if error:
        logger.error(f"OAuth error from {provider}: {error} - {error_description}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error={error}&message={error_description or 'Authentication failed'}",
            status_code=303
        )
    
    # Verify state parameter
    if not state or not sso_service.verify_state(state):
        logger.warning(f"Invalid state parameter for {provider} callback")
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=invalid_state&message=Invalid authentication state",
            status_code=303
        )
    
    if not code:
        logger.warning(f"No authorization code in {provider} callback")
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=no_code&message=No authorization code received",
            status_code=303
        )
    
    try:
        # Get OAuth client
        oauth_client = sso_service.get_provider(provider)
        
        # Exchange authorization code for token
        redirect_uri = f"{settings.base_url}/api/sso/{provider}/callback"
        token = await oauth_client.authorize_access_token(
            request,
            redirect_uri=redirect_uri,
            code=code
        )
        
        # Extract user information from token
        user_info = await sso_service.get_user_info(provider, token)
        
        # Get or create user
        user = await sso_service.get_or_create_user(db, user_info)
        
        # Create JWT token
        jwt_token = sso_service.create_jwt_token(user)
        
        # Redirect to frontend with token
        # In production, consider using a more secure method like:
        # 1. Setting a secure, httpOnly cookie
        # 2. Using a temporary token exchange endpoint
        # 3. Posting to parent window if using popup flow
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/callback?token={jwt_token}&provider={provider}",
            status_code=303
        )
        
    except OAuthError as e:
        logger.error(f"OAuth error during {provider} callback: {str(e)}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=oauth_error&message={str(e)}",
            status_code=303
        )
    except Exception as e:
        logger.error(f"Unexpected error during {provider} callback: {str(e)}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=server_error&message=Authentication failed. Please try again.",
            status_code=303
        )


@router.get("/providers")
async def get_available_providers():
    """Get list of configured SSO providers."""
    
    providers = []
    
    if settings.google_client_id:
        providers.append({
            "name": "google",
            "display_name": "Google",
            "icon": "google"
        })
    
    if settings.github_client_id:
        providers.append({
            "name": "github",
            "display_name": "GitHub",
            "icon": "github"
        })
    
    if settings.azure_client_id:
        providers.append({
            "name": "azure",
            "display_name": "Microsoft",
            "icon": "microsoft"
        })
    
    if settings.orcid_client_id:
        providers.append({
            "name": "orcid",
            "display_name": "ORCID",
            "icon": "orcid"
        })
    
    return {"providers": providers}