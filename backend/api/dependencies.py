"""API dependencies and middleware utilities."""

from fastapi import Header, HTTPException, status

from backend.config.settings import settings


async def require_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> None:
    expected = settings.api_key
    if not expected or x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

