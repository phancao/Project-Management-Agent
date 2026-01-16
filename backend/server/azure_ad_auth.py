# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Azure AD (Office 365) OAuth Authentication Module

Provides SSO authentication using Microsoft Azure AD for enterprise users.
Implements OAuth 2.0 Authorization Code flow with PKCE.

Environment Variables Required:
- AUTH_AZURE_AD_CLIENT_ID: Azure AD Application (client) ID
- AUTH_AZURE_AD_CLIENT_SECRET: Azure AD Client Secret
- AUTH_AZURE_AD_TENANT_ID: Azure AD Directory (tenant) ID
- AUTH_URL: Base URL for OAuth callbacks (e.g., http://localhost:8000)
"""

import os
import logging
import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Azure AD Configuration from environment
AZURE_AD_CLIENT_ID = os.getenv("AUTH_AZURE_AD_CLIENT_ID", "")
AZURE_AD_CLIENT_SECRET = os.getenv("AUTH_AZURE_AD_CLIENT_SECRET", "")
AZURE_AD_TENANT_ID = os.getenv("AUTH_AZURE_AD_TENANT_ID", "")
AUTH_URL = os.getenv("AUTH_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")
# Callback path - set this to match what's registered in Azure Portal
# Common values: "", "/callback", "/auth/callback", "/api/auth/callback/azure-ad"
AUTH_CALLBACK_PATH = os.getenv("AUTH_CALLBACK_PATH", "")

# Azure AD OAuth endpoints
AUTHORITY = f"https://login.microsoftonline.com/{AZURE_AD_TENANT_ID}"
AUTHORIZATION_ENDPOINT = f"{AUTHORITY}/oauth2/v2.0/authorize"
TOKEN_ENDPOINT = f"{AUTHORITY}/oauth2/v2.0/token"
GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0/me"

# OAuth scopes
SCOPES = ["openid", "profile", "email", "User.Read"]

# State storage for CSRF protection (in production, use Redis or DB)
_oauth_states: dict[str, dict] = {}

router = APIRouter(tags=["Azure AD OAuth"])


class AzureTokenResponse(BaseModel):
    """Response from Azure AD token endpoint"""
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    id_token: Optional[str] = None
    refresh_token: Optional[str] = None


class AzureUserInfo(BaseModel):
    """User info from Microsoft Graph API"""
    id: str
    displayName: Optional[str] = None
    mail: Optional[str] = None
    userPrincipalName: Optional[str] = None


def _validate_azure_config():
    """Check if Azure AD is properly configured."""
    if not all([AZURE_AD_CLIENT_ID, AZURE_AD_CLIENT_SECRET, AZURE_AD_TENANT_ID]):
        raise HTTPException(
            status_code=500,
            detail="Azure AD SSO is not configured. Please set AUTH_AZURE_AD_CLIENT_ID, AUTH_AZURE_AD_CLIENT_SECRET, and AUTH_AZURE_AD_TENANT_ID environment variables."
        )


@router.get("/azure/login")
async def azure_login(redirect_uri: Optional[str] = None):
    """
    Initiate Azure AD OAuth login flow.
    
    Redirects user to Microsoft login page.
    
    Args:
        redirect_uri: Optional custom redirect URI after successful login
    """
    _validate_azure_config()
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Store state with optional redirect info
    _oauth_states[state] = {
        "redirect_uri": redirect_uri or f"{FRONTEND_URL}/pm/chat"
    }
    
    # Build authorization URL using configurable callback path
    callback_url = f"{AUTH_URL}{AUTH_CALLBACK_PATH}"
    
    params = {
        "client_id": AZURE_AD_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": callback_url,
        "response_mode": "query",
        "scope": " ".join(SCOPES),
        "state": state,
        "prompt": "select_account",  # Always show account picker
    }
    
    authorization_url = f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"
    
    logger.info(f"[Azure AD] Redirecting to Microsoft login, state={state[:8]}...")
    
    return RedirectResponse(url=authorization_url)


# Alias route for NextAuth pattern (matches Azure Portal registration)
@router.get("/callback/azure-ad")
async def azure_callback_alias(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
):
    """Alias for azure_callback - matches NextAuth URL pattern."""
    return await azure_callback(code, state, error, error_description)


@router.get("/azure/callback")
async def azure_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
):
    """
    Handle OAuth callback from Azure AD.
    
    Exchanges authorization code for tokens, fetches user info,
    and creates/updates user in database.
    """
    _validate_azure_config()
    
    # Handle OAuth errors
    if error:
        logger.error(f"[Azure AD] OAuth error: {error} - {error_description}")
        # Redirect to login page with error
        error_url = f"{FRONTEND_URL}/login?error={error}&error_description={error_description}"
        return RedirectResponse(url=error_url)
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing authorization code or state")
    
    # Validate state for CSRF protection
    if state not in _oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    state_data = _oauth_states.pop(state)
    final_redirect = state_data.get("redirect_uri", f"{FRONTEND_URL}/pm/chat")
    
    # Exchange code for tokens (redirect_uri must match exactly what was used in login)
    callback_url = f"{AUTH_URL}{AUTH_CALLBACK_PATH}"
    
    token_data = {
        "client_id": AZURE_AD_CLIENT_ID,
        "client_secret": AZURE_AD_CLIENT_SECRET,
        "code": code,
        "redirect_uri": callback_url,
        "grant_type": "authorization_code",
        "scope": " ".join(SCOPES),
    }
    
    async with httpx.AsyncClient() as client:
        # Get tokens from Azure AD
        token_response = await client.post(
            TOKEN_ENDPOINT,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if token_response.status_code != 200:
            logger.error(f"[Azure AD] Token exchange failed: {token_response.text}")
            error_url = f"{FRONTEND_URL}/login?error=token_exchange_failed"
            return RedirectResponse(url=error_url)
        
        tokens = token_response.json()
        access_token = tokens.get("access_token")
        
        # Get user info from Microsoft Graph
        user_response = await client.get(
            GRAPH_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if user_response.status_code != 200:
            logger.error(f"[Azure AD] User info fetch failed: {user_response.text}")
            error_url = f"{FRONTEND_URL}/login?error=user_info_failed"
            return RedirectResponse(url=error_url)
        
        azure_user = user_response.json()
    
    # Extract user info
    azure_id = azure_user.get("id")
    email = azure_user.get("mail") or azure_user.get("userPrincipalName")
    display_name = azure_user.get("displayName") or email.split("@")[0] if email else "User"
    
    if not email:
        logger.error(f"[Azure AD] No email in user profile: {azure_user}")
        error_url = f"{FRONTEND_URL}/login?error=no_email"
        return RedirectResponse(url=error_url)
    
    logger.info(f"[Azure AD] User authenticated: {email}")
    
    # Create or update user in database
    from database.connection import get_db_session
    from database.orm_models import User
    from backend.server.web_auth import create_access_token
    
    db_gen = get_db_session()
    db = next(db_gen)
    
    try:
        # Check if user exists by Azure AD ID or email
        user = db.query(User).filter(
            (User.azure_ad_id == azure_id) | (User.email == email)
        ).first()
        
        if user:
            # Update existing user with Azure AD info
            if not user.azure_ad_id:
                user.azure_ad_id = azure_id
                user.oauth_provider = "azure_ad"
                logger.info(f"[Azure AD] Linked existing user {email} to Azure AD")
            db.commit()
        else:
            # Create new user
            user = User(
                email=email,
                name=display_name,
                azure_ad_id=azure_id,
                oauth_provider="azure_ad",
                role="user",
                # No password_hash for OAuth users
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"[Azure AD] Created new user: {email}")
        
        # Generate our JWT token
        jwt_token, expires_in = create_access_token(
            user_id=str(user.id),
            email=user.email,
            name=user.name,
            role=user.role or "user",
        )
        
        # Redirect to login page with token - it will store the token and redirect to final destination
        # The login page handles OAuth callback params (token, user_id, etc.)
        from urllib.parse import quote
        redirect_url = f"{FRONTEND_URL}/login?token={jwt_token}&user_id={user.id}&user_email={quote(user.email)}&user_name={quote(user.name)}"
        
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"[Azure AD] Database error: {e}", exc_info=True)
        db.rollback()
        error_url = f"{FRONTEND_URL}/login?error=database_error"
        return RedirectResponse(url=error_url)
    finally:
        db.close()


@router.get("/azure/status")
async def azure_status():
    """Check if Azure AD SSO is configured."""
    configured = all([AZURE_AD_CLIENT_ID, AZURE_AD_CLIENT_SECRET, AZURE_AD_TENANT_ID])
    return {
        "enabled": configured,
        "tenant_id": AZURE_AD_TENANT_ID if configured else None,
        "client_id": AZURE_AD_CLIENT_ID if configured else None,
    }
