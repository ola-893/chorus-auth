"""
Auth0 JWT verification helpers backed by JWKS.
"""
from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.request import urlopen

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import HTTPException, status

from ..control_plane_config import settings


def _b64url_decode(value: str) -> bytes:
    padding_length = (-len(value)) % 4
    return base64.urlsafe_b64decode(f"{value}{'=' * padding_length}")


@dataclass
class Auth0TokenClaims:
    """Normalized claims returned after JWT verification."""

    sub: str
    email: str | None
    name: str | None
    nickname: str | None
    claims: dict[str, Any]


class Auth0JwtVerifier:
    """Verify Auth0 access tokens against a JWKS endpoint."""

    def __init__(self) -> None:
        self._jwks_cache: dict[str, dict[str, Any]] = {}
        self._jwks_cached_at: float = 0.0

    def verify(self, token: str) -> Auth0TokenClaims:
        """Verify the provided bearer token and return normalized claims."""
        try:
            encoded_header, encoded_payload, encoded_signature = token.split(".")
        except ValueError as exc:  # pragma: no cover - defensive
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed bearer token",
            ) from exc

        header = self._decode_json_segment(encoded_header)
        payload = self._decode_json_segment(encoded_payload)

        if header.get("alg") != "RS256":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unsupported JWT signing algorithm",
            )

        kid = header.get("kid")
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing JWT key identifier",
            )

        jwk = self._get_signing_key(kid)
        public_key = self._public_key_for_jwk(jwk)
        signature = _b64url_decode(encoded_signature)
        signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")

        try:
            public_key.verify(
                signature,
                signing_input,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except Exception as exc:  # pragma: no cover - crypto failure path
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="JWT signature verification failed",
            ) from exc

        self._validate_claims(payload)
        return Auth0TokenClaims(
            sub=str(payload["sub"]),
            email=payload.get("email"),
            name=payload.get("name"),
            nickname=payload.get("nickname"),
            claims=payload,
        )

    def _validate_claims(self, payload: dict[str, Any]) -> None:
        expected_issuer = settings.auth0_issuer or self._derive_issuer()
        expected_audience = settings.auth0_audience
        now = int(time.time())
        exp = payload.get("exp")
        iss = payload.get("iss")
        aud = payload.get("aud")

        if not payload.get("sub"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token subject")

        if exp is None or int(exp) <= now:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token has expired")

        if iss != expected_issuer:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT issuer does not match Auth0 configuration")

        if expected_audience:
            audiences = aud if isinstance(aud, list) else [aud]
            if expected_audience not in audiences:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT audience does not match the configured API audience")

    def _get_signing_key(self, kid: str) -> dict[str, Any]:
        now = time.time()
        cache_ttl = settings.auth0_jwks_cache_ttl_seconds
        if not self._jwks_cache or (now - self._jwks_cached_at) > cache_ttl:
            self._jwks_cache = {
                key["kid"]: key
                for key in self._fetch_jwks().get("keys", [])
                if key.get("kid")
            }
            self._jwks_cached_at = now

        key = self._jwks_cache.get(kid)
        if key is None:
            self._jwks_cache = {
                item["kid"]: item
                for item in self._fetch_jwks().get("keys", [])
                if item.get("kid")
            }
            self._jwks_cached_at = now
            key = self._jwks_cache.get(kid)

        if key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to resolve JWT signing key",
            )
        return key

    def _fetch_jwks(self) -> dict[str, Any]:
        jwks_url = settings.auth0_jwks_url or f"{self._derive_issuer()}.well-known/jwks.json"
        with urlopen(jwks_url, timeout=settings.auth0_http_timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _derive_issuer(self) -> str:
        if settings.auth0_domain:
            normalized = settings.auth0_domain.rstrip("/")
            if not normalized.startswith("http"):
                normalized = f"https://{normalized}"
            return f"{normalized}/"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth0 domain is not configured",
        )

    def _decode_json_segment(self, value: str) -> dict[str, Any]:
        try:
            return json.loads(_b64url_decode(value).decode("utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="JWT payload could not be decoded",
            ) from exc

    def _public_key_for_jwk(self, jwk: dict[str, Any]) -> rsa.RSAPublicKey:
        try:
            modulus = int.from_bytes(_b64url_decode(jwk["n"]), "big")
            exponent = int.from_bytes(_b64url_decode(jwk["e"]), "big")
        except KeyError as exc:  # pragma: no cover - defensive
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="JWT signing key is incomplete",
            ) from exc

        return rsa.RSAPublicNumbers(exponent, modulus).public_key()


jwt_verifier = Auth0JwtVerifier()
