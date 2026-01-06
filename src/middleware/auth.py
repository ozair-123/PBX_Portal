"""
Authentication middleware for request tracking and optional JWT extraction.

This middleware:
1. Extracts JWT token from request if present (for logging/audit)
2. Adds request ID for distributed tracing
3. Does NOT enforce authentication (use RBAC decorators for that)
"""

import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from src.auth.jwt import JWTManager
import logging

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track authenticated requests and add request context.

    This middleware extracts user information from JWT tokens if present,
    but does NOT enforce authentication. Use RBAC decorators on endpoints
    for authentication enforcement.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add authentication context.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain

        Returns:
            HTTP response
        """
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Extract JWT token if present (optional - for logging/audit)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = JWTManager.verify_token(token, token_type="access")

            if payload:
                # Store user context in request state (available to endpoints)
                request.state.user_id = payload.get("user_id")
                request.state.user_role = payload.get("role")
                request.state.tenant_id = payload.get("tenant_id")
                request.state.authenticated = True
            else:
                request.state.authenticated = False
        else:
            request.state.authenticated = False

        # Process request
        response = await call_next(request)

        # Add request ID to response headers for client-side tracing
        response.headers["X-Request-ID"] = request_id

        # Log request completion (for audit trail)
        if hasattr(request.state, "user_id"):
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"[User: {request.state.user_id}, Role: {request.state.user_role}, "
                f"Request ID: {request_id}, Status: {response.status_code}]"
            )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware (placeholder for future enhancement).

    TODO: Implement proper rate limiting with Redis or in-memory store.
    For now, this is a placeholder that logs requests.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting (not yet implemented).

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain

        Returns:
            HTTP response
        """
        # TODO: Implement rate limiting logic
        # For now, just pass through
        response = await call_next(request)
        return response
