# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Web Authentication Module for Frontend Login

Provides:
- JWT token generation and validation for frontend sessions
- Password hashing with bcrypt
- Auth middleware for protected API endpoints

This is separate from MCP API key auth (which is for Cursor/VS Code clients).
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Request
from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production-12345")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==================== Pydantic Models ====================

class LoginRequest(BaseModel):
    """Login request body"""
    email: str
    password: str


class RegisterRequest(BaseModel):
    """Registration request body"""
    email: EmailStr
    password: str
    name: str


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: dict


class UserResponse(BaseModel):
    """User info response"""
    id: str
    email: str
    name: str
    role: str


# ==================== Password Utilities ====================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt. Truncates to 72 bytes (bcrypt limit)."""
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')[:72]
    return pwd_context.hash(password_bytes.decode('utf-8', errors='ignore'))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash. Truncates to 72 bytes."""
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = plain_password.encode('utf-8')[:72]
    return pwd_context.verify(password_bytes.decode('utf-8', errors='ignore'), hashed_password)


# ==================== JWT Utilities ====================

def create_access_token(user_id: str, email: str, name: str, role: str = "user") -> tuple[str, int]:
    """
    Create a JWT access token for a user.
    
    Returns:
        tuple: (token_string, expires_in_seconds)
    """
    expires_delta = timedelta(hours=JWT_EXPIRATION_HOURS)
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "sub": user_id,  # subject (user ID)
        "email": email,
        "name": name,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    expires_in = int(expires_delta.total_seconds())
    
    return token, expires_in


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.
    
    Returns:
        dict: Token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


# ==================== Auth Middleware ====================

async def get_current_user_from_request(request: Request) -> Optional[dict]:
    """
    Extract and validate user from Authorization header.
    
    Returns:
        dict with user info or None if no auth
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        return None
    
    if not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    
    try:
        payload = decode_access_token(token)
        return {
            "id": payload.get("sub"),
            "email": payload.get("email"),
            "name": payload.get("name"),
            "role": payload.get("role", "user"),
        }
    except HTTPException:
        return None


async def require_auth(request: Request) -> dict:
    """
    Require authentication for an endpoint.
    
    Returns:
        dict with user info
        
    Raises:
        HTTPException 401 if not authenticated
    """
    user = await get_current_user_from_request(request)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide Authorization: Bearer <token> header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_user_id_from_request(request: Request) -> Optional[str]:
    """
    Synchronous helper to get user ID from request.
    For use in sync code paths.
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header[7:]
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
