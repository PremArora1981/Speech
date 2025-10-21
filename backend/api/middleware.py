"""API middleware for rate limiting, authentication, and request tracking."""

from __future__ import annotations

import time
from typing import Callable, Optional
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.config.settings import settings
from backend.utils.logging import get_logger


logger = get_logger(__name__)


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    For production, consider using Redis-backed rate limiting for:
    - Distributed rate limiting across multiple instances
    - Persistence across restarts
    - Better performance at scale
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute per identifier
            requests_per_hour: Maximum requests per hour per identifier
            burst_size: Maximum burst requests allowed
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size

        # Store: {identifier: [(timestamp, count), ...]}
        self.minute_windows: dict[str, list[tuple[float, int]]] = defaultdict(list)
        self.hour_windows: dict[str, list[tuple[float, int]]] = defaultdict(list)
        self.burst_counts: dict[str, int] = defaultdict(int)
        self.last_burst_reset: dict[str, float] = defaultdict(float)

    def _clean_old_entries(
        self, windows: dict[str, list[tuple[float, int]]], window_seconds: int
    ) -> None:
        """Remove entries older than the window."""
        cutoff = time.time() - window_seconds
        for identifier in list(windows.keys()):
            windows[identifier] = [
                (ts, count) for ts, count in windows[identifier] if ts > cutoff
            ]
            if not windows[identifier]:
                del windows[identifier]

    def _get_count(self, windows: list[tuple[float, int]]) -> int:
        """Get total count from windows."""
        return sum(count for _, count in windows)

    def check_rate_limit(self, identifier: str) -> tuple[bool, Optional[int]]:
        """
        Check if request is within rate limits.

        Args:
            identifier: Unique identifier (IP address or API key)

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        now = time.time()

        # Clean old entries
        self._clean_old_entries(self.minute_windows, 60)
        self._clean_old_entries(self.hour_windows, 3600)

        # Check burst limit (reset every second)
        if now - self.last_burst_reset.get(identifier, 0) >= 1.0:
            self.burst_counts[identifier] = 0
            self.last_burst_reset[identifier] = now

        if self.burst_counts[identifier] >= self.burst_size:
            return False, 1  # Retry after 1 second

        # Check minute limit
        minute_count = self._get_count(self.minute_windows[identifier])
        if minute_count >= self.requests_per_minute:
            oldest_timestamp = self.minute_windows[identifier][0][0]
            retry_after = int(60 - (now - oldest_timestamp)) + 1
            return False, retry_after

        # Check hour limit
        hour_count = self._get_count(self.hour_windows[identifier])
        if hour_count >= self.requests_per_hour:
            oldest_timestamp = self.hour_windows[identifier][0][0]
            retry_after = int(3600 - (now - oldest_timestamp)) + 1
            return False, retry_after

        # Allow request and update counters
        self.minute_windows[identifier].append((now, 1))
        self.hour_windows[identifier].append((now, 1))
        self.burst_counts[identifier] += 1

        return True, None

    def get_stats(self, identifier: str) -> dict:
        """Get current rate limit stats for an identifier."""
        now = time.time()
        self._clean_old_entries(self.minute_windows, 60)
        self._clean_old_entries(self.hour_windows, 3600)

        minute_count = self._get_count(self.minute_windows[identifier])
        hour_count = self._get_count(self.hour_windows[identifier])

        return {
            "requests_last_minute": minute_count,
            "requests_last_hour": hour_count,
            "minute_limit": self.requests_per_minute,
            "hour_limit": self.requests_per_hour,
            "minute_remaining": max(0, self.requests_per_minute - minute_count),
            "hour_remaining": max(0, self.requests_per_hour - hour_count),
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests.

    Applies different rate limits based on:
    - IP address (for unauthenticated requests)
    - API key (for authenticated requests)
    - Endpoint type (stricter limits for expensive operations)
    """

    def __init__(
        self,
        app: ASGIApp,
        default_limiter: Optional[RateLimiter] = None,
        websocket_limiter: Optional[RateLimiter] = None,
        strict_limiter: Optional[RateLimiter] = None,
    ):
        super().__init__(app)

        # Default limiter for most endpoints (relaxed for development)
        self.default_limiter = default_limiter or RateLimiter(
            requests_per_minute=300,  # Increased for development
            requests_per_hour=10000,
            burst_size=50,
        )

        # Lenient limiter for WebSocket connections
        self.websocket_limiter = websocket_limiter or RateLimiter(
            requests_per_minute=500,  # Increased for development
            requests_per_hour=10000,
            burst_size=100,  # Allow rapid reconnection attempts
        )

        # Strict limiter for expensive operations (relaxed for development)
        self.strict_limiter = strict_limiter or RateLimiter(
            requests_per_minute=50,  # Increased for development
            requests_per_hour=500,
            burst_size=10,
        )

        # Paths that should use strict rate limiting
        self.strict_paths = [
            "/api/v1/telephony/calls",  # Outbound calls are expensive
            "/api/v1/rag/ingest",  # Document ingestion is expensive
        ]

        # Paths that should be excluded from rate limiting
        self.excluded_paths = [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
        ]

    def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting."""
        # Use API key if available (more specific than IP)
        api_key = request.headers.get("X-API-Key") or request.headers.get("api-subscription-key")
        if api_key:
            return f"key:{api_key[:16]}"  # Use first 16 chars to avoid long keys

        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return f"ip:{forwarded_for.split(',')[0].strip()}"

        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    def _select_limiter(self, request: Request) -> RateLimiter:
        """Select appropriate rate limiter based on request."""
        path = request.url.path

        # WebSocket connections get lenient limits
        if path.startswith("/api/v1/voice-session"):
            return self.websocket_limiter

        # Expensive operations get strict limits
        if any(path.startswith(strict_path) for strict_path in self.strict_paths):
            return self.strict_limiter

        # Default limiter for everything else
        return self.default_limiter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        path = request.url.path

        # Skip WebSocket upgrade requests
        if request.headers.get("upgrade") == "websocket":
            return await call_next(request)

        # Skip rate limiting for excluded paths
        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return await call_next(request)

        # Get identifier and limiter
        identifier = self._get_identifier(request)
        limiter = self._select_limiter(request)

        # Check rate limit
        is_allowed, retry_after = limiter.check_rate_limit(identifier)

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for {identifier} on {path}",
                extra={
                    "identifier": identifier,
                    "path": path,
                    "method": request.method,
                    "retry_after": retry_after,
                },
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded. Retry after {retry_after} seconds.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Get stats for response headers
        stats = limiter.get_stats(identifier)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(stats["minute_limit"])
        response.headers["X-RateLimit-Remaining-Minute"] = str(stats["minute_remaining"])
        response.headers["X-RateLimit-Limit-Hour"] = str(stats["hour_limit"])
        response.headers["X-RateLimit-Remaining-Hour"] = str(stats["hour_remaining"])

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all API requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        start_time = time.time()

        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
            },
        )

        # Process request
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                f"Response: {response.status_code} ({duration_ms:.2f}ms)",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

            # Add timing header
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            return response

        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {exc} ({duration_ms:.2f}ms)",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(exc),
                },
                exc_info=True,
            )
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""

    def __init__(
        self,
        app: ASGIApp,
        hsts_max_age: int = 31536000,
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
    ):
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HSTS header
        hsts_value = f"max-age={self.hsts_max_age}"
        if self.hsts_include_subdomains:
            hsts_value += "; includeSubDomains"
        if self.hsts_preload:
            hsts_value += "; preload"
        response.headers["Strict-Transport-Security"] = hsts_value

        # Content Security Policy (basic)
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        # CORS headers (if needed - usually handled by FastAPI's CORSMiddleware)
        # response.headers["Access-Control-Allow-Origin"] = "*"

        return response


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware for redirecting HTTP requests to HTTPS.

    Only applies in production environments.
    """

    def __init__(self, app: ASGIApp, enabled: bool = False):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Redirect HTTP to HTTPS if enabled."""
        if not self.enabled:
            return await call_next(request)

        # Check if request is over HTTP
        if request.url.scheme == "http":
            # Check X-Forwarded-Proto header (for reverse proxies)
            forwarded_proto = request.headers.get("X-Forwarded-Proto", "").lower()

            if forwarded_proto != "https":
                # Redirect to HTTPS
                https_url = request.url.replace(scheme="https")
                return JSONResponse(
                    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                    headers={"Location": str(https_url)},
                    content={"detail": "Redirecting to HTTPS"},
                )

        return await call_next(request)
