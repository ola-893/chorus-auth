# Environment Variables

This document covers the active environment variables for the Chorus auth control plane MVP.

## Core Runtime

| Variable | Default | Purpose |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | Runtime environment label exposed through health and meta endpoints. |
| `API_HOST` | `0.0.0.0` | Host interface for the FastAPI server. |
| `API_PORT` | `8000` | Port used by the FastAPI server. |
| `DATABASE_URL` | `sqlite:///./data/chorus.db` | Primary relational store for users, agents, actions, approvals, and audit events. |
| `CORS_ALLOWED_ORIGINS` | local Vite and preview origins | Comma-separated origins allowed to call the backend from the browser. |

## Demo Seeding

| Variable | Default | Purpose |
| --- | --- | --- |
| `SEED_DEMO` | `true` | Enables the seeded demo workspace. |
| `SEED_ON_STARTUP` | `true` | Reseeds the demo workspace on startup for a repeatable local run. |
| `QUARANTINE_AFTER_BLOCKED_REQUESTS` | `2` | Number of blocked requests before an agent is quarantined. |
| `ALLOW_DEMO_MODE` | `true` | Allows the frontend to request local demo-mode auth fallback. |

## Auth And Vault

| Variable | Default | Purpose |
| --- | --- | --- |
| `AUTH_MODE` | `mock` | Authentication mode. Use `mock` locally and `auth0` when wiring a real tenant. |
| `VAULT_MODE` | `mock` | Token Vault adapter mode. |
| `PROVIDER_MODE` | `mock` | Provider adapter mode. |
| `ALLOW_PROVIDER_FALLBACK` | `true` | Allows live provider adapters to fall back to clearly labeled mock execution on failure. |
| `AUTH0_DOMAIN` | unset | Auth0 domain for live auth integration. |
| `AUTH0_ISSUER` | unset | Optional explicit issuer override for JWT validation. |
| `AUTH0_AUDIENCE` | unset | Audience for live Auth0 validation. |
| `AUTH0_CLIENT_ID` | unset | Client id for the Auth0 application. |
| `AUTH0_JWKS_URL` | unset | Optional explicit JWKS URL override. |
| `AUTH0_SCOPE` | `openid profile email offline_access` | Scope requested by the SPA login flow. |
| `TOKEN_VAULT_AUDIENCE` | unset | Audience for live Token Vault access. |
| `TOKEN_VAULT_BASE_URL` | unset | Base URL for the Token Vault HTTP API. |
| `TOKEN_VAULT_CLIENT_ID` | unset | Token Vault client id. |
| `TOKEN_VAULT_CLIENT_SECRET` | unset | Token Vault client secret. |
| `TOKEN_VAULT_GOOGLE_CONNECTION` | `google-oauth2` | Token Vault connection name for Gmail. |
| `TOKEN_VAULT_GITHUB_CONNECTION` | `github` | Token Vault connection name for GitHub. |
| `GMAIL_API_BASE_URL` | `https://gmail.googleapis.com` | Base URL used by the Gmail provider adapter in live mode. |
| `GITHUB_API_BASE_URL` | `https://api.github.com` | Base URL used by the GitHub provider adapter in live mode. |

## Risk And LLM

| Variable | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | unset | Optional API key for contextual risk explanations. |
| `GEMINI_MODEL` | `gemini-3-pro-preview` | Gemini model used by the risk adapter. |

## Frontend

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Frontend API base URL for local or hosted previews. |

## Notes

- In the default seeded demo, mock auth and mock vault behavior are enough to exercise the full approval and quarantine story.
- Postgres is supported by setting `DATABASE_URL` to a `postgresql+psycopg://...` value.
- No separate broker or cache service is required for the default local demo path.
