"""SourceScout — identifies online data sources for hardware products.

Uses Google Gemini to discover relevant subreddits, review sites,
and hardware forums for a given product.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


from chasm.core.config import settings
from chasm.core.llm import GeminiAgent
from chasm.core.logger import get_logger

logger = get_logger(__name__)


class SourceScout(GeminiAgent):
    """Discover online sources of hardware feedback via LLM."""

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _ask_json_list(self, prompt: str) -> list[str]:
        """Send a prompt to Gemini and parse the response as a JSON list of strings."""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        raw = response.text or "[]"
        logger.debug("Raw LLM response:\n%s", raw)

        # Strip markdown fences if present
        raw = re.sub(r"```(?:json)?\s*", "", raw).strip()

        # Find the JSON array in the response
        match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if not match:
            logger.error("No JSON array found in LLM response:\n%s", raw)
            return []

        try:
            result = json.loads(match.group(0))
            if isinstance(result, list):
                return [str(item) for item in result]
            return []
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from LLM response:\n%s", raw)
            return []

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def identify_subreddits(self, product_name: str) -> list[str]:
        """Identify top subreddits where people discuss a hardware product.

        Args:
            product_name: The name of the hardware product to research.

        Returns:
            A list of subreddit names (e.g. ``["r/drones", "r/dji"]``).
        """
        prompt = (
            f"You are a hardware research assistant. What are the top 3-5 "
            f"subreddits where people discuss the hardware, components, or "
            f"issues of {product_name} or its specific category? "
            f"Return ONLY a valid JSON list of strings "
            f"(e.g., [\"r/drones\", \"r/hardware\"])."
        )
        logger.info("Identifying subreddits for: %s", product_name)
        results = self._ask_json_list(prompt)
        logger.info("Found %d subreddit(s) for %s", len(results), product_name)
        return results

    def find_review_sites(self, product_name: str) -> list[str]:
        """Find authoritative review and teardown sites for a hardware product.

        Args:
            product_name: The name of the hardware product to research.

        Returns:
            A list of domain names (e.g. ``["rtings.com", "ifixit.com"]``).
        """
        prompt = (
            f"What are the top 3 authoritative review websites, teardown "
            f"sites, or hardware forums for {product_name}? "
            f"Return ONLY a valid JSON list of domain names "
            f"(e.g., [\"rtings.com\", \"ifixit.com\"])."
        )
        logger.info("Finding review sites for: %s", product_name)
        results = self._ask_json_list(prompt)
        logger.info("Found %d review site(s) for %s", len(results), product_name)
        return results
