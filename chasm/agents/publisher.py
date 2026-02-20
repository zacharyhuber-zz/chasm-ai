"""WeeklyBriefing — generate a Monday Morning Briefing from the Knowledge Graph.

Queries recent Insight nodes, sends them to Gemini for executive-level
summarisation, and saves the resulting Markdown report to disk.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


from chasm.core.config import settings
from chasm.core.llm import GeminiAgent
from chasm.core.logger import get_logger
from chasm.graph.builder import ChasmGraph

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Briefing prompt template
# ---------------------------------------------------------------------------

_BRIEFING_PROMPT = """\
You are a World-Class Hardware Product Manager. You are writing a weekly \
update for your executive team regarding the '{product_name}'.

Below is a list of raw insights gathered from Reddit and web reviews this week:
{insights}

Your task: Write a 'Monday Morning Briefing' in Markdown.
Structure it as follows:
- ## Executive Summary: (2 sentences on the overall 'vibe' this week).
- ## Critical Hardware Alerts: (Highlight any negative trends related to \
specific components like Battery, Hinge, etc.)
- ## The 'Internal vs. External' Drift: (Note if users are complaining about \
things engineering thinks are 'fine').
- ## Suggested Action Items: (Top 3 things the PO should investigate this week).

Keep the tone professional, data-driven, and brief."""


class WeeklyBriefing(GeminiAgent):
    """Generate and save executive-level weekly briefings from graph insights."""

    # ------------------------------------------------------------------
    # 1. Query the graph for recent insights
    # ------------------------------------------------------------------

    def get_new_insights(
        self,
        graph: ChasmGraph,
        days_back: int = 7,
    ) -> list[dict]:
        """Collect Insight nodes added within the last *days_back* days.

        For each Insight, also resolves the related Component name via the
        outgoing ABOUT edge and the Source sentiment.

        Args:
            graph: A populated ChasmGraph.
            days_back: Look-back window in days.

        Returns:
            A list of dicts with keys: id, summary, sentiment, tags,
            component_name, source_url.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        results: list[dict] = []

        for nid, data in graph.graph.nodes(data=True):
            if data.get("node_type") != "Insight":
                continue

            # Check date_added if present, otherwise include everything
            date_added = data.get("date_added")
            if date_added:
                try:
                    if datetime.fromisoformat(str(date_added)) < cutoff:
                        continue
                except (ValueError, TypeError):
                    pass

            # Resolve component via ABOUT edge
            component_name = "General"
            source_url = ""
            for _, target, edge_data in graph.graph.out_edges(nid, data=True):
                if edge_data.get("relation") == "ABOUT":
                    target_data = graph.graph.nodes.get(target, {})
                    component_name = target_data.get("name", "General")

            # Resolve source via incoming YIELDS edge
            for src, _, edge_data in graph.graph.in_edges(nid, data=True):
                if edge_data.get("relation") == "YIELDS":
                    src_data = graph.graph.nodes.get(src, {})
                    source_url = src_data.get("url", "")

            results.append({
                "id": nid,
                "summary": data.get("summary", ""),
                "sentiment": data.get("sentiment", 0.0),
                "tags": data.get("tags", []),
                "component_name": component_name,
                "source_url": source_url,
            })

        logger.info(
            "Found %d insight(s) within the last %d day(s).",
            len(results),
            days_back,
        )
        return results

    # ------------------------------------------------------------------
    # 2. Generate the briefing via LLM
    # ------------------------------------------------------------------

    def generate_summary(
        self,
        product_name: str,
        insights: list[dict],
    ) -> str:
        """Send insights to Gemini and return a formatted Monday Morning Briefing.

        Args:
            product_name: Human-readable product name.
            insights: List of insight dicts (from get_new_insights).

        Returns:
            Markdown string with the full briefing.
        """
        # Format insights as a readable list for the prompt
        insight_lines: list[str] = []
        for i, ins in enumerate(insights, 1):
            sentiment = ins.get("sentiment", 0.0)
            component = ins.get("component_name", "General")
            summary = ins.get("summary", "")
            tags = ", ".join(ins.get("tags", []))
            insight_lines.append(
                f"{i}. [{component}] {summary} "
                f"(sentiment: {sentiment}, tags: {tags})"
            )

        insights_text = "\n".join(insight_lines) if insight_lines else "(No insights this week)"

        prompt = _BRIEFING_PROMPT.format(
            product_name=product_name,
            insights=insights_text,
        )

        logger.info("Generating Monday Morning Briefing for '%s' …", product_name)

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        report = response.text or "(No report generated)"
        logger.info("Briefing generated (%d chars).", len(report))
        return report

    # ------------------------------------------------------------------
    # 3. Save report to disk
    # ------------------------------------------------------------------

    def save_report(self, report_md: str, product_id: str) -> Path:
        """Save the briefing as a dated Markdown file.

        Args:
            report_md: The full Markdown briefing string.
            product_id: Groups the report under ``chasm/reports/{product_id}/``.

        Returns:
            Path to the created file.
        """
        out_dir = settings.reports_dir / product_id
        out_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = out_dir / f"weekly_briefing_{date_str}.md"

        filepath.write_text(report_md, encoding="utf-8")
        logger.info("Report saved to %s (%d bytes)", filepath, len(report_md))
        return filepath
