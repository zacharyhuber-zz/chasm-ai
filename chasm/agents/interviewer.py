"""Interviewer — AI-powered conversational employee interview agent.

Conducts a friendly, one-question-at-a-time interview covering:
  1. Employee thoughts on the company's products
  2. What updates they think should be made
  3. Additional opportunities for the company

Also provides InterviewInsightExtractor to convert completed
transcripts into structured (Component, Insight) pairs.
"""

from __future__ import annotations

import json
import re
from uuid import uuid4

from chasm.core.llm import GeminiAgent
from chasm.core.logger import get_logger
from chasm.models.schema import Component, ComponentCategory, Insight

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Category mapping (reused from extractor.py)
# ---------------------------------------------------------------------------

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
    lower = component_name.lower()
    for keyword, cat in _CATEGORY_MAP.items():
        if keyword in lower:
            return cat
    return ComponentCategory.UNKNOWN


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_INTERVIEW_SYSTEM = """\
You are a friendly, empathetic interviewer working for a hardware product company.
Your job is to have a natural, conversational interview with an employee to understand their perspective.

RULES:
- Ask only ONE question at a time. Wait for the employee's response before asking the next question.
- Be warm, encouraging, and professional. Acknowledge their answers before moving on.
- Keep questions open-ended to encourage detailed responses.
- Do NOT ask all questions at once — this must feel like a real conversation.

INTERVIEW FLOW (guide the conversation through these areas naturally):
1. Start with a warm introduction and ask which product(s) they work on or are most familiar with.
2. Ask what they think is working well with the product(s).
3. Ask what challenges or issues they see with the product(s).
4. Ask what specific updates or improvements they would recommend.
5. Ask about new opportunities — features, markets, or innovations the company should explore.
6. Ask if there's anything else they'd like to share.
7. Thank them sincerely and let them know their feedback is valuable.

When the conversation has covered all topics (typically 5-7 exchanges), end with a thank-you message
that includes the exact phrase "Thank you for your time" so the system can detect completion.

CONTEXT: The company makes the following products: {product_names}
"""

_EXTRACTION_PROMPT = """\
You are a Hardware Product Manager analyzing an employee interview transcript.
Extract specific, actionable insights from this interview.

Return ONLY a valid JSON list of objects with the following keys:
- "product_name" (str): The product being discussed (use the closest match from the known products, or "General" if unclear).
- "component_name" (str): The physical part or system discussed (e.g., "Battery", "Screen", "Firmware"). Use "General" for whole-product or company-level feedback.
- "summary" (str): A concise 1-sentence summary of the insight.
- "sentiment" (float): A score from -1.0 (very negative) to 1.0 (very positive).
- "tags" (list of str): 2-3 categorical tags.

Known products: {product_names}

Interview transcript:
{transcript}"""


# ---------------------------------------------------------------------------
# Interviewer Agent
# ---------------------------------------------------------------------------

class Interviewer(GeminiAgent):
    """Conversational AI agent that conducts employee interviews."""

    def start_interview(self, product_names: str) -> str:
        """Generate the opening greeting for a new interview.

        Args:
            product_names: Comma-separated names of all company products.

        Returns:
            The AI's opening message.
        """
        system = _INTERVIEW_SYSTEM.format(product_names=product_names)

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                {"role": "user", "parts": [{"text": system + "\n\nPlease begin the interview with a friendly greeting."}]},
            ],
        )
        return (response.text or "").strip()

    def next_turn(
        self,
        conversation_history: list[dict],
        product_names: str,
    ) -> str:
        """Generate the AI's next response given the conversation so far.

        Args:
            conversation_history: List of {"role": "assistant"|"user", "content": str}.
            product_names: Comma-separated names of all company products.

        Returns:
            The AI's next message.
        """
        system = _INTERVIEW_SYSTEM.format(product_names=product_names)

        # Build the Gemini contents array
        contents = []

        # First message includes the system prompt
        for i, msg in enumerate(conversation_history):
            role = "model" if msg["role"] == "assistant" else "user"
            text = msg["content"]
            if i == 0 and role == "model":
                # Prepend system prompt context to the first assistant message
                text = f"[System: {system}]\n\n{text}"
            contents.append({"role": role, "parts": [{"text": text}]})

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
        )
        return (response.text or "").strip()


# ---------------------------------------------------------------------------
# Transcript → Insights extractor
# ---------------------------------------------------------------------------

class InterviewInsightExtractor(GeminiAgent):
    """Extract structured insights from a completed interview transcript."""

    def extract_from_transcript(
        self,
        transcript: str,
        product_names: str,
    ) -> list[tuple[Component, Insight, str]]:
        """Process a transcript and return typed models.

        Args:
            transcript: The full Q&A transcript text.
            product_names: Comma-separated product names for context.

        Returns:
            List of (Component, Insight, product_name_hint) tuples.
        """
        prompt = _EXTRACTION_PROMPT.format(
            product_names=product_names,
            transcript=transcript[:20_000],
        )

        logger.info("Extracting insights from interview transcript …")
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        raw = response.text or "[]"
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            logger.error("No JSON array in LLM response:\n%s", raw)
            return []

        try:
            items: list[dict] = json.loads(match.group(0))
        except json.JSONDecodeError:
            logger.error("Unparseable JSON from LLM:\n%s", raw)
            return []

        results: list[tuple[Component, Insight, str]] = []
        for item in items:
            comp_name = item.get("component_name", "General")
            component = Component(
                id=f"comp-{uuid4().hex[:8]}",
                name=comp_name,
                category=_guess_category(comp_name),
            )

            sentiment_val = max(-1.0, min(1.0, float(item.get("sentiment", 0.0))))
            insight = Insight(
                id=f"ins-interview-{uuid4().hex[:8]}",
                summary=item.get("summary", ""),
                sentiment=sentiment_val,
                tags=item.get("tags", []),
            )

            product_hint = item.get("product_name", "General")
            results.append((component, insight, product_hint))

        logger.info("Extracted %d insight(s) from interview.", len(results))
        return results
