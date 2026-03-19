"""OpportunityGenerator — synthesise opportunities and personas from graph data.

Analyses all Insight nodes for a product and uses Gemini to produce:
  1. Typed Opportunity objects (unmet needs, friction points, etc.)
  2. Persona segments with Jobs-to-be-Done
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from chasm.core.llm import GeminiAgent
from chasm.core.logger import get_logger
from chasm.models.schema import (
    JobToBeDone,
    Opportunity,
    OpportunityType,
    Persona,
    Severity,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_OPPORTUNITY_PROMPT = """\
You are a senior Product Strategist analysing customer and employee feedback
for the product "{product_name}".

Below is a list of insights extracted from web reviews, Reddit discussions,
employee interviews, and other sources. Each insight has an ID, a summary,
a sentiment score (-1 negative to +1 positive), and tags.

INSIGHTS:
{insights_json}

From these insights, identify **5 to 10 discrete product opportunities**.
For each opportunity, determine:
- "title": A short, specific title (e.g., "Enterprise users creating manual workarounds for data export")
- "opportunity_type": One of "Unmet Need", "Friction Point", "Revenue Risk", "Feature Request"
- "severity": "High", "Medium", or "Low"
- "summary": A 2-3 sentence explanation of the opportunity and why it matters
- "persona_tags": Which customer segments are affected (e.g., ["Enterprise Admins", "Power Users"])
- "evidence_node_ids": The IDs of insights that support this opportunity (from the list above)

PRIORITISATION RULES:
- High severity: affects many users, strong negative sentiment, or revenue risk
- Medium severity: moderate impact, mixed sentiment, or feature gap
- Low severity: nice-to-have, positive sentiment but room for improvement

Return ONLY a valid JSON list of opportunity objects. No markdown, no explanation.
"""

_PERSONA_PROMPT = """\
You are a senior Product Strategist analysing feedback for "{product_name}".

Below are the insights and opportunities you have identified:

INSIGHTS:
{insights_json}

OPPORTUNITIES:
{opportunities_json}

From this data, identify **3 to 5 distinct customer persona segments**.
For each persona:
- "name": A descriptive segment name (e.g., "Mid-Market Sales Execs", "Field Technicians")
- "description": A 1-2 sentence description of who this persona is
- "jobs_to_be_done": A list of 2-4 Jobs-to-be-Done this persona is trying to accomplish.
  Each job should have:
  - "title": What they're trying to do
  - "status": "underserved", "partially_met", or "well_served"
  - "evidence_node_ids": Insight IDs that relate to this job

Return ONLY a valid JSON list of persona objects. No markdown, no explanation.
"""


def _parse_json_list(raw: str) -> list[dict]:
    """Extract a JSON list from LLM output, tolerating markdown fences."""
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return []
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return []


class OpportunityGenerator(GeminiAgent):
    """Generate Opportunity and Persona objects from graph insight data."""

    def _collect_insights(
        self,
        graph,
        product_id: str,
    ) -> list[dict[str, Any]]:
        """Gather all Insight nodes linked to a product's components."""
        insights: list[dict[str, Any]] = []
        seen: set[str] = set()

        for _, comp_id, edge in graph.graph.out_edges(product_id, data=True):
            if edge.get("relation") != "HAS_COMPONENT":
                continue
            # Find insights pointing at this component via ABOUT
            for src_id, _, e2 in graph.graph.in_edges(comp_id, data=True):
                if e2.get("relation") != "ABOUT":
                    continue
                node = graph.graph.nodes.get(src_id)
                if not node or node.get("node_type") != "Insight":
                    continue
                if src_id in seen:
                    continue
                seen.add(src_id)
                insights.append({
                    "id": src_id,
                    "summary": node.get("summary", ""),
                    "sentiment": node.get("sentiment", 0),
                    "tags": node.get("tags", []),
                })

        return insights

    def generate_opportunities(
        self,
        graph,
        product_id: str,
        product_name: str,
    ) -> list[Opportunity]:
        """Analyse graph insights and return typed Opportunity objects."""
        insights = self._collect_insights(graph, product_id)

        if not insights:
            logger.warning(
                "No insights found for product %s — skipping opportunity generation.",
                product_id,
            )
            return []

        logger.info(
            "Generating opportunities for '%s' from %d insights …",
            product_name,
            len(insights),
        )

        prompt = _OPPORTUNITY_PROMPT.format(
            product_name=product_name,
            insights_json=json.dumps(insights, indent=2),
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        items = _parse_json_list(response.text or "[]")
        now = datetime.now(timezone.utc).isoformat()

        # Map string values to enums safely
        type_map = {t.value: t for t in OpportunityType}
        severity_map = {s.value: s for s in Severity}

        opportunities: list[Opportunity] = []
        for item in items:
            try:
                opp = Opportunity(
                    id=f"opp-{uuid4().hex[:8]}",
                    title=item.get("title", "Untitled"),
                    opportunity_type=type_map.get(
                        item.get("opportunity_type", ""),
                        OpportunityType.UNMET_NEED,
                    ),
                    severity=severity_map.get(
                        item.get("severity", ""),
                        Severity.MEDIUM,
                    ),
                    summary=item.get("summary", ""),
                    persona_tags=item.get("persona_tags", []),
                    evidence_node_ids=item.get("evidence_node_ids", []),
                    product_id=product_id,
                    created_at=now,
                )
                opportunities.append(opp)
            except Exception as exc:
                logger.warning("Skipping malformed opportunity: %s", exc)

        logger.info("Generated %d opportunity(ies) for '%s'.", len(opportunities), product_name)
        return opportunities

    def generate_personas(
        self,
        graph,
        product_id: str,
        product_name: str,
        opportunities: list[Opportunity],
    ) -> list[Persona]:
        """Analyse insights + opportunities and return typed Persona objects."""
        insights = self._collect_insights(graph, product_id)

        if not insights:
            return []

        logger.info(
            "Generating personas for '%s' from %d insights …",
            product_name,
            len(insights),
        )

        prompt = _PERSONA_PROMPT.format(
            product_name=product_name,
            insights_json=json.dumps(insights, indent=2),
            opportunities_json=json.dumps(
                [o.model_dump(mode="json") for o in opportunities],
                indent=2,
            ),
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        items = _parse_json_list(response.text or "[]")

        personas: list[Persona] = []
        for item in items:
            try:
                jobs = [
                    JobToBeDone(
                        title=j.get("title", ""),
                        status=j.get("status", "underserved"),
                        evidence_node_ids=j.get("evidence_node_ids", []),
                    )
                    for j in item.get("jobs_to_be_done", [])
                ]
                persona = Persona(
                    id=f"persona-{uuid4().hex[:8]}",
                    name=item.get("name", "Unknown Segment"),
                    description=item.get("description", ""),
                    jobs_to_be_done=jobs,
                    product_id=product_id,
                )
                personas.append(persona)
            except Exception as exc:
                logger.warning("Skipping malformed persona: %s", exc)

        logger.info("Generated %d persona(s) for '%s'.", len(personas), product_name)
        return personas
