# Environment Variables

This document covers the active environment variables for the Chorus auth control plane MVP.

## Core Runtime

| Variable | Default | Purpose |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | Runtime environment label exposed through health and meta endpoints. |
| `API_HOST` | `0.0.0.0` | Host interface for the FastAPI server. |
| `API_PORT` | `8000` | Port used by the FastAPI server. |
| `DATABASE_URL` | `sqlite:///./data/chorus.db` | Primary relational store for users, agents, actions, approvals, and audit events. |

## Demo Seeding

| Variable | Default | Purpose |
| --- | --- | --- |
| `SEED_DEMO` | `true` | Enables the seeded demo workspace. |
| `SEED_ON_STARTUP` | `true` | Reseeds the demo workspace on startup for a repeatable local run. |
| `QUARANTINE_AFTER_BLOCKED_REQUESTS` | `2` | Number of blocked requests before an agent is quarantined. |

## Auth And Vault

| Variable | Default | Purpose |
| --- | --- | --- |
| `AUTH_MODE` | `mock` | Authentication mode. Use `mock` locally and `auth0` when wiring a real tenant. |
| `VAULT_MODE` | `mock` | Token Vault adapter mode. |
| `PROVIDER_MODE` | `mock` | Provider adapter mode. |
| `AUTH0_DOMAIN` | unset | Auth0 domain for live auth integration. |
| `AUTH0_AUDIENCE` | unset | Audience for live Auth0 validation. |
| `AUTH0_CLIENT_ID` | unset | Client id for the Auth0 application. |
| `TOKEN_VAULT_AUDIENCE` | unset | Audience for live Token Vault access. |
| `TOKEN_VAULT_CLIENT_ID` | unset | Token Vault client id. |
| `TOKEN_VAULT_CLIENT_SECRET` | unset | Token Vault client secret. |

## Risk And LLM

| Variable | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | unset | Optional API key for contextual risk explanations. |
| `GEMINI_MODEL` | `gemini-3-pro-preview` | Gemini model used by the risk adapter. |

## Notes

- In the default seeded demo, mock auth and mock vault behavior are enough to exercise the full approval and quarantine story.
- No separate broker or cache service is required for the default local demo path.
