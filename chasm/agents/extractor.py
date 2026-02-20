"""InsightExtractor — extract hardware insights from scraped Markdown via LLM.

Reads Markdown files with YAML frontmatter (produced by the Harvesters),
sends the content to Gemini for structured extraction, and returns
typed Pydantic models ready for graph injection.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4

import yaml

from chasm.core.config import settings
from chasm.core.llm import GeminiAgent
from chasm.core.logger import get_logger
from chasm.models.schema import (
    Component,
    ComponentCategory,
    Insight,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Extraction prompt template
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """\
You are a Hardware Product Manager analyzing customer feedback for the {product_name}.
Read the following text and extract specific actionable insights.
Return ONLY a valid JSON list of objects with the following keys:
- "component_name" (str): The physical part being discussed (e.g., "Battery", "Screen", "Hinge"). Use "General" if it's about the whole product.
- "summary" (str): A concise 1-sentence summary of the feedback.
- "sentiment" (float): A score from -1.0 (very negative) to 1.0 (very positive).
- "tags" (list of str): 2-3 categorical tags (e.g., ["thermal", "safety"]).

Text to analyze:
{text_content}"""

# Map common component mentions to a category
_CATEGORY_MAP: dict[str, ComponentCategory] = {
    "battery": ComponentCategory.ELECTRICAL,
    "motor": ComponentCategory.ELECTRICAL,
    "power": ComponentCategory.ELECTRICAL,
    "charger": ComponentCategory.ELECTRICAL,
    "esc": ComponentCategory.ELECTRICAL,
    "sensor": ComponentCategory.ELECTRICAL,
    "camera": ComponentCategory.ELECTRICAL,
    "gimbal": ComponentCategory.MECHANICAL,
    "hinge": ComponentCategory.MECHANICAL,
    "propeller": ComponentCategory.MECHANICAL,
    "arm": ComponentCategory.MECHANICAL,
    "landing gear": ComponentCategory.MECHANICAL,
    "frame": ComponentCategory.MECHANICAL,
    "screen": ComponentCategory.ELECTRICAL,
    "firmware": ComponentCategory.FIRMWARE,
    "software": ComponentCategory.FIRMWARE,
    "app": ComponentCategory.FIRMWARE,
    "box": ComponentCategory.PACKAGING,
    "packaging": ComponentCategory.PACKAGING,
}


def _guess_category(component_name: str) -> ComponentCategory:
    """Best-effort category mapping from a free-text component name."""
    lower = component_name.lower()
    for keyword, cat in _CATEGORY_MAP.items():
        if keyword in lower:
            return cat
    return ComponentCategory.UNKNOWN


class InsightExtractor(GeminiAgent):
    """Extract hardware insights from scraped Markdown using Gemini."""

    # ------------------------------------------------------------------
    # 1. Parse Markdown
    # ------------------------------------------------------------------

    @staticmethod
    def parse_markdown_file(filepath: str) -> dict:
        """Read a Markdown file and separate frontmatter from body.

        Args:
            filepath: Path to a ``.md`` file with YAML frontmatter.

        Returns:
            ``{"frontmatter": dict, "content": str}``
        """
        text = Path(filepath).read_text(encoding="utf-8")

        # Split on the YAML delimiters (--- ... ---)
        parts = text.split("---", maxsplit=2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1]) or {}
            content = parts[2].strip()
        else:
            frontmatter = {}
            content = text.strip()

        return {"frontmatter": frontmatter, "content": content}

    # ------------------------------------------------------------------
    # 2. Extract insights via LLM
    # ------------------------------------------------------------------

    def extract_insights(self, text_content: str, product_name: str) -> list[dict]:
        """Send text to Gemini and extract structured insight dicts.

        Args:
            text_content: The body text to analyse.
            product_name: Product name for prompt context.

        Returns:
            A list of dicts with keys: component_name, summary, sentiment, tags.
        """
        prompt = _EXTRACTION_PROMPT.format(
            product_name=product_name,
            text_content=text_content[:15_000],  # cap context
        )

        logger.info("Extracting insights for '%s' …", product_name)

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        raw = response.text or "[]"
        logger.debug("Raw LLM response:\n%s", raw)

        # Find the JSON array
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            logger.error("No JSON array in LLM response:\n%s", raw)
            return []

        try:
            items: list[dict] = json.loads(match.group(0))
        except json.JSONDecodeError:
            logger.error("Unparseable JSON from LLM:\n%s", raw)
            return []

        logger.info("Extracted %d insight(s).", len(items))
        return items

    # ------------------------------------------------------------------
    # 3. Process a directory of scraped files
    # ------------------------------------------------------------------

    def process_directory(
        self,
        raw_dir: str,
        product_id: str,
        product_name: str,
    ) -> list[tuple[Component, Insight, str]]:
        """Process all ``.md`` files in a directory and return typed models.

        Args:
            raw_dir: Path to the directory containing scraped Markdown files.
            product_id: The product these files belong to.
            product_name: Human-readable product name for prompts.

        Returns:
            A list of ``(Component, Insight, source_url)`` tuples ready for
            injection into ``ChasmGraph``.
        """
        raw_path = Path(raw_dir)
        md_files = sorted(raw_path.glob("*.md"))
        logger.info(
            "Processing %d file(s) in %s for product '%s'",
            len(md_files),
            raw_dir,
            product_name,
        )

        results: list[tuple[Component, Insight, str]] = []

        for md_file in md_files:
            parsed = self.parse_markdown_file(str(md_file))
            source_url = parsed["frontmatter"].get("source_url", str(md_file))

            raw_insights = self.extract_insights(parsed["content"], product_name)

            for item in raw_insights:
                comp_name = item.get("component_name", "General")
                component = Component(
                    id=f"comp-{uuid4().hex[:8]}",
                    name=comp_name,
                    category=_guess_category(comp_name),
                )

                sentiment_val = item.get("sentiment", 0.0)
                # Clamp to [-1, 1]
                sentiment_val = max(-1.0, min(1.0, float(sentiment_val)))

                insight = Insight(
                    id=f"ins-{uuid4().hex[:8]}",
                    summary=item.get("summary", ""),
                    sentiment=sentiment_val,
                    tags=item.get("tags", []),
                )

                results.append((component, insight, source_url))

        logger.info(
            "Directory processing complete: %d (Component, Insight) pairs.",
            len(results),
        )
        return results
