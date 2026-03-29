"""
Configuration for the auth control plane runtime.
"""
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ControlPlaneSettings(BaseSettings):
    """Settings for the auth control plane MVP."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )

    app_name: str = Field(default="Chorus Auth Control Plane")
    environment: str = Field(default="development")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    database_url: str = Field(default="sqlite:///./data/chorus.db")
    cors_allowed_origins_csv: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
    )
    auth_mode: str = Field(default="mock")
    allow_demo_mode: bool = Field(default=True)
    vault_mode: str = Field(default="mock")
    provider_mode: str = Field(default="mock")
    seed_demo: bool = Field(default=True)
    seed_on_startup: bool = Field(default=True)
    quarantine_after_blocked_requests: int = Field(default=2)
    auth0_domain: Optional[str] = Field(default=None)
    auth0_issuer: Optional[str] = Field(default=None)
    auth0_audience: Optional[str] = Field(default=None)
    auth0_client_id: Optional[str] = Field(default=None)
    auth0_jwks_url: Optional[str] = Field(default=None)
    auth0_scope: str = Field(default="openid profile email")
    auth0_http_timeout_seconds: float = Field(default=5.0)
    auth0_jwks_cache_ttl_seconds: int = Field(default=600)
    token_vault_audience: Optional[str] = Field(default=None)
    token_vault_base_url: Optional[str] = Field(default=None)
    token_vault_client_id: Optional[str] = Field(default=None)
    token_vault_client_secret: Optional[str] = Field(default=None)
    token_vault_google_connection: str = Field(default="google-oauth2")
    token_vault_github_connection: str = Field(default="github")
    token_vault_timeout_seconds: float = Field(default=10.0)
    allow_provider_fallback: bool = Field(default=True)
    gmail_api_base_url: str = Field(default="https://gmail.googleapis.com")
    github_api_base_url: str = Field(default="https://api.github.com")
    gemini_api_key: Optional[str] = Field(default=None)
    gemini_model: str = Field(default="gemini-3-pro-preview")

    def cors_allowed_origins(self) -> list[str]:
        """Return normalized CORS origins for local or hosted previews."""
        return [origin.strip() for origin in self.cors_allowed_origins_csv.split(",") if origin.strip()]

    def mode_summary(self) -> dict:
        """Return non-sensitive mode information for health and diagnostics."""
        return {
            "auth_mode": self.auth_mode,
            "allow_demo_mode": self.allow_demo_mode,
            "vault_mode": self.vault_mode,
            "provider_mode": self.provider_mode,
            "seed_demo": self.seed_demo,
            "allow_provider_fallback": self.allow_provider_fallback,
        }


settings = ControlPlaneSettings()
