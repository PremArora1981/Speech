"""TLS/HTTPS configuration for production deployment."""

from __future__ import annotations

import ssl
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class TLSConfig(BaseModel):
    """TLS configuration settings."""

    enabled: bool = Field(default=False, description="Enable TLS/HTTPS")
    cert_path: Optional[str] = Field(default=None, description="Path to SSL certificate file")
    key_path: Optional[str] = Field(default=None, description="Path to SSL private key file")
    ca_certs: Optional[str] = Field(default=None, description="Path to CA certificates bundle")
    verify_mode: str = Field(default="CERT_REQUIRED", description="SSL verification mode")
    min_version: str = Field(default="TLSv1_2", description="Minimum TLS version")
    ciphers: Optional[str] = Field(
        default=None,
        description="Allowed cipher suites (None = default secure ciphers)",
    )

    def create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """
        Create SSL context for the server.

        Returns:
            SSLContext if TLS is enabled, None otherwise
        """
        if not self.enabled:
            return None

        if not self.cert_path or not self.key_path:
            raise ValueError("TLS enabled but cert_path or key_path not provided")

        # Validate files exist
        cert_file = Path(self.cert_path)
        key_file = Path(self.key_path)

        if not cert_file.exists():
            raise FileNotFoundError(f"Certificate file not found: {self.cert_path}")
        if not key_file.exists():
            raise FileNotFoundError(f"Key file not found: {self.key_path}")

        # Create SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

        # Load certificate and private key
        context.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))

        # Set minimum TLS version
        min_version_map = {
            "TLSv1_2": ssl.TLSVersion.TLSv1_2,
            "TLSv1_3": ssl.TLSVersion.TLSv1_3,
        }
        context.minimum_version = min_version_map.get(
            self.min_version, ssl.TLSVersion.TLSv1_2
        )

        # Set verification mode
        verify_mode_map = {
            "CERT_NONE": ssl.CERT_NONE,
            "CERT_OPTIONAL": ssl.CERT_OPTIONAL,
            "CERT_REQUIRED": ssl.CERT_REQUIRED,
        }
        context.verify_mode = verify_mode_map.get(self.verify_mode, ssl.CERT_REQUIRED)

        # Load CA certificates if provided
        if self.ca_certs:
            ca_file = Path(self.ca_certs)
            if ca_file.exists():
                context.load_verify_locations(cafile=str(ca_file))

        # Set cipher suites if provided
        if self.ciphers:
            context.set_ciphers(self.ciphers)
        else:
            # Use secure default ciphers (Mozilla Modern compatibility)
            context.set_ciphers(
                "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
            )

        # Additional security settings
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        context.options |= ssl.OP_NO_COMPRESSION
        context.options |= ssl.OP_SINGLE_DH_USE
        context.options |= ssl.OP_SINGLE_ECDH_USE

        return context


class HTTPSRedirectConfig(BaseModel):
    """Configuration for HTTP to HTTPS redirection."""

    enabled: bool = Field(default=False, description="Enable HTTP to HTTPS redirect")
    http_port: int = Field(default=80, description="HTTP port to redirect from")
    https_port: int = Field(default=443, description="HTTPS port to redirect to")
    hsts_max_age: int = Field(
        default=31536000,
        description="HSTS max-age in seconds (1 year)",
    )
    hsts_include_subdomains: bool = Field(
        default=True,
        description="Include subdomains in HSTS",
    )
    hsts_preload: bool = Field(default=False, description="Enable HSTS preload")


# Default configurations for different environments
DEV_TLS_CONFIG = TLSConfig(
    enabled=False  # TLS typically not needed in local development
)

PRODUCTION_TLS_CONFIG = TLSConfig(
    enabled=True,
    cert_path="/etc/ssl/certs/speech-backend.crt",
    key_path="/etc/ssl/private/speech-backend.key",
    ca_certs="/etc/ssl/certs/ca-certificates.crt",
    verify_mode="CERT_REQUIRED",
    min_version="TLSv1_3",  # Use TLS 1.3 for maximum security
)

PRODUCTION_HTTPS_REDIRECT = HTTPSRedirectConfig(
    enabled=True,
    http_port=80,
    https_port=443,
    hsts_max_age=31536000,
    hsts_include_subdomains=True,
    hsts_preload=False,
)


def get_tls_config(environment: str = "development") -> TLSConfig:
    """
    Get TLS configuration for the specified environment.

    Args:
        environment: Environment name (development, staging, production)

    Returns:
        TLSConfig instance
    """
    if environment in ("production", "staging"):
        return PRODUCTION_TLS_CONFIG
    return DEV_TLS_CONFIG


def get_https_redirect_config(environment: str = "development") -> HTTPSRedirectConfig:
    """
    Get HTTPS redirect configuration for the specified environment.

    Args:
        environment: Environment name (development, staging, production)

    Returns:
        HTTPSRedirectConfig instance
    """
    if environment in ("production", "staging"):
        return PRODUCTION_HTTPS_REDIRECT
    return HTTPSRedirectConfig(enabled=False)
