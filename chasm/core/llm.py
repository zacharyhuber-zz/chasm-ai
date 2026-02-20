"""Shared LLM base class for Gemini-powered agents.

Provides a common __init__ that loads the API key from central config
and initialises the google-genai client.  All Chasm agents that talk
to Gemini should inherit from GeminiAgent.
"""

from __future__ import annotations

from google import genai

from chasm.core.config import settings
from chasm.core.logger import get_logger

logger = get_logger(__name__)


class GeminiAgent:
    """Base class for agents that use Google Gemini."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model = model or settings.gemini_model
        resolved_key = api_key or settings.google_api_key
        if not resolved_key:
            raise EnvironmentError(
                "GOOGLE_API_KEY not found. Set it in .env or pass api_key=."
            )
        self.client = genai.Client(api_key=resolved_key)
        logger.info("%s ready (model=%s)", self.__class__.__name__, self.model)
