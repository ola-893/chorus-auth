"""
Provider adapters with live execution and explicit mock fallback labels.
"""
from __future__ import annotations

import base64
from email.message import EmailMessage
from uuid import uuid4

import httpx

from ..control_plane_config import settings
from ..db.enums import ProviderType
from ..vault.adapters import ProviderAccess
from .base import ProviderAdapter, ProviderExecutionResult


class GmailProviderAdapter:
    """Gmail adapter supporting live draft creation with mock fallback."""

    def execute(
        self,
        capability_name: str,
        payload: dict,
        access: ProviderAccess,
    ) -> ProviderExecutionResult:
        if settings.provider_mode == "live" and access.access_token:
            try:
                return self._execute_live(payload, access)
            except Exception as exc:
                if not settings.allow_provider_fallback:
                    raise
                return self._execute_mock(payload, access, fallback_reason=str(exc))
        return self._execute_mock(payload, access)

    def _execute_live(self, payload: dict, access: ProviderAccess) -> ProviderExecutionResult:
        message = EmailMessage()
        recipients = payload.get("to", [])
        message["To"] = ", ".join(recipients)
        message["Subject"] = payload.get("subject", "")
        message.set_content(payload.get("body", ""))
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{settings.gmail_api_base_url.rstrip('/')}/gmail/v1/users/me/drafts",
                headers={"Authorization": f"Bearer {access.access_token}"},
                json={"message": {"raw": encoded_message}},
            )
        response.raise_for_status()
        body = response.json()
        draft = body.get("draft", body)
        draft_id = draft.get("id")
        return ProviderExecutionResult(
            success=True,
            summary=f"Created live Gmail draft for {len(recipients)} recipient(s).",
            external_reference_id=draft_id,
            result_url="https://mail.google.com/mail/u/0/#drafts",
            execution_mode="live",
            payload={
                "draft_id": draft_id,
                "recipient_count": len(recipients),
                "vault_reference": access.reference,
            },
        )

    def _execute_mock(
        self,
        payload: dict,
        access: ProviderAccess,
        fallback_reason: str | None = None,
    ) -> ProviderExecutionResult:
        recipients = payload.get("to", [])
        draft_id = f"draft-{uuid4()}"
        summary = f"Created Gmail draft for {len(recipients)} recipient(s)."
        if fallback_reason:
            summary = f"{summary} Live execution fell back to mock mode."
        return ProviderExecutionResult(
            success=True,
            summary=summary,
            external_reference_id=draft_id,
            result_url=None,
            execution_mode="mock-fallback" if fallback_reason else "mock",
            payload={
                "draft_id": draft_id,
                "recipient_count": len(recipients),
                "vault_reference": access.reference,
                "fallback_reason": fallback_reason,
            },
        )


class GitHubProviderAdapter:
    """GitHub adapter supporting live issue creation with mock fallback."""

    def execute(
        self,
        capability_name: str,
        payload: dict,
        access: ProviderAccess,
    ) -> ProviderExecutionResult:
        if settings.provider_mode == "live" and access.access_token and capability_name == "github.issue.create":
            try:
                return self._execute_live_issue(payload, access)
            except Exception as exc:
                if not settings.allow_provider_fallback:
                    raise
                return self._execute_mock(capability_name, payload, access, fallback_reason=str(exc))
        return self._execute_mock(capability_name, payload, access)

    def _execute_live_issue(self, payload: dict, access: ProviderAccess) -> ProviderExecutionResult:
        repository = payload.get("repository", "")
        owner, repo = repository.split("/", 1)
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{settings.github_api_base_url.rstrip('/')}/repos/{owner}/{repo}/issues",
                headers={
                    "Authorization": f"Bearer {access.access_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                json={
                    "title": payload.get("title", "Chorus managed issue"),
                    "body": payload.get("body", ""),
                },
            )
        response.raise_for_status()
        body = response.json()
        issue_number = body.get("number")
        return ProviderExecutionResult(
            success=True,
            summary=f"Created live GitHub issue for {repository}.",
            external_reference_id=str(issue_number) if issue_number is not None else None,
            result_url=body.get("html_url"),
            execution_mode="live",
            payload={
                "repository": repository,
                "issue_number": issue_number,
                "vault_reference": access.reference,
            },
        )

    def _execute_mock(
        self,
        capability_name: str,
        payload: dict,
        access: ProviderAccess,
        fallback_reason: str | None = None,
    ) -> ProviderExecutionResult:
        reference_id = f"github-{uuid4()}"
        repository = payload.get("repository", "unknown")
        action_label = "issue" if capability_name == "github.issue.create" else "pull request action"
        summary = f"Created {action_label} event for {repository}."
        if fallback_reason:
            summary = f"{summary} Live execution fell back to mock mode."
        return ProviderExecutionResult(
            success=True,
            summary=summary,
            external_reference_id=reference_id,
            result_url=None,
            execution_mode="mock-fallback" if fallback_reason else "mock",
            payload={
                "repository": repository,
                "reference_id": reference_id,
                "vault_reference": access.reference,
                "fallback_reason": fallback_reason,
            },
        )


class ProviderRegistry:
    """Lookup provider adapters by provider type."""

    def __init__(self) -> None:
        self._providers: dict[ProviderType, ProviderAdapter] = {
            ProviderType.GMAIL: GmailProviderAdapter(),
            ProviderType.GITHUB: GitHubProviderAdapter(),
        }

    def get(self, provider: ProviderType) -> ProviderAdapter:
        return self._providers[provider]


provider_registry = ProviderRegistry()
