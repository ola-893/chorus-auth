"""
Optional Gemini enrichment for risk explanations.
"""
from typing import Optional

try:
    import google.genai as genai
except ImportError:  # pragma: no cover - handled in runtime fallback
    genai = None

from ..control_plane_config import settings


class GeminiRiskAdapter:
    """Small wrapper around Gemini for contextual risk explanations."""

    def explain(
        self,
        provider: str,
        capability_name: str,
        payload: dict,
        policy_reason: str,
    ) -> Optional[str]:
        if not settings.gemini_api_key or genai is None:
            return None

        prompt = (
            "You are evaluating delegated AI agent actions.\n"
            f"Provider: {provider}\n"
            f"Capability: {capability_name}\n"
            f"Payload: {payload}\n"
            f"Policy context: {policy_reason}\n"
            "Return a short, plain-English risk explanation in one sentence."
        )

        try:
            client = genai.Client(api_key=settings.gemini_api_key)
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
            )
            text = getattr(response, "text", None)
            if not text:
                return None
            return text.strip()
        except Exception:
            return None
