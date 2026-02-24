"""Interview session model and file-based persistence.

Each interview session is stored as a JSON file under
``chasm/data/interviews/{session_id}.json``.  When a session is completed,
insights are extracted from the transcript via InsightExtractor and
injected into the Knowledge Graph with SourceType.EMPLOYEE_INTERVIEW.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from chasm.core.config import settings
from chasm.core.logger import get_logger

logger = get_logger(__name__)

# Directory where interview session files live
INTERVIEWS_DIR = settings.project_root / "chasm" / "data" / "interviews"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """A single message in the interview conversation."""
    role: str = Field(..., description="'assistant' or 'user'")
    content: str = Field(..., description="The message text")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )


class InterviewSession(BaseModel):
    """Represents a single employee interview session."""
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    status: str = Field(default="pending", description="pending | active | completed")
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    completed_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _session_path(session_id: str) -> Path:
    return INTERVIEWS_DIR / f"{session_id}.json"


def create_session() -> InterviewSession:
    """Create a new empty interview session and persist it."""
    INTERVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    session = InterviewSession()
    save_session(session)
    logger.info("Created interview session %s", session.id)
    return session


def load_session(session_id: str) -> InterviewSession | None:
    """Load a session from disk, or return None if not found."""
    path = _session_path(session_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return InterviewSession(**data)


def save_session(session: InterviewSession) -> None:
    """Persist session state to disk."""
    INTERVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    path = _session_path(session.id)
    path.write_text(
        session.model_dump_json(indent=2),
        encoding="utf-8",
    )


def list_sessions() -> list[InterviewSession]:
    """Return all sessions on disk."""
    if not INTERVIEWS_DIR.exists():
        return []
    sessions = []
    for p in sorted(INTERVIEWS_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            sessions.append(InterviewSession(**data))
        except Exception:
            logger.warning("Skipping invalid session file: %s", p)
    return sessions


# ---------------------------------------------------------------------------
# Completion → Graph injection
# ---------------------------------------------------------------------------

def complete_session(session: InterviewSession) -> int:
    """Mark session as completed and inject insights into the graph.

    Returns:
        The number of insights injected.
    """
    from chasm.agents.interviewer import InterviewInsightExtractor
    from chasm.api.deps import get_graph
    from chasm.graph.persistence import save_graph_to_disk
    from chasm.models.schema import Source, SourceType

    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc).isoformat()
    save_session(session)

    # Build transcript text from user messages
    transcript = "\n\n".join(
        f"Q: {session.messages[i - 1].content}\nA: {msg.content}"
        for i, msg in enumerate(session.messages)
        if msg.role == "user" and i > 0
    )

    if not transcript.strip():
        logger.warning("Session %s has no user messages to extract.", session.id)
        return 0

    # Extract insights from the transcript
    extractor = InterviewInsightExtractor()
    graph = get_graph()

    # Get all products from the graph
    product_nodes = [
        (nid, data)
        for nid, data in graph.graph.nodes(data=True)
        if data.get("node_type") == "Product"
    ]

    if not product_nodes:
        logger.warning("No products in graph; cannot attach interview insights.")
        return 0

    product_names = ", ".join(d.get("name", nid) for nid, d in product_nodes)
    results = extractor.extract_from_transcript(transcript, product_names)

    injected = 0
    for component, insight, product_id_hint in results:
        # Try to match the product_id_hint to a real product
        target_product_id = product_nodes[0][0]  # default to first
        for pid, pdata in product_nodes:
            if pdata.get("name", "").lower() in product_id_hint.lower():
                target_product_id = pid
                break

        graph.add_component(component, product_id=target_product_id)

        source = Source(
            id=f"src-interview-{insight.id}",
            type=SourceType.EMPLOYEE_INTERVIEW,
            raw_text=insight.summary,
            url=f"interview://{session.id}",
        )
        graph.add_source(source)
        graph.add_insight(
            insight=insight,
            source_id=source.id,
            target_id=component.id,
        )
        injected += 1

    # Generate embeddings for the new interview insights and run semantic linking
    # so they are connected to existing insights immediately (not just on weekly run)
    if injected > 0:
        from chasm.vector.engine import VectorEngine

        vector_engine = VectorEngine()
        for nid, data in graph.graph.nodes(data=True):
            if data.get("node_type") == "Insight" and not data.get("embedding"):
                summary = data.get("summary", "")
                if summary:
                    embedding = vector_engine.generate_embedding(summary)
                    graph.graph.nodes[nid]["embedding"] = embedding

        vector_engine.link_semantic_matches(graph.graph)

    save_graph_to_disk(graph)
    logger.info(
        "Session %s completed: injected %d insight(s) into graph.",
        session.id,
        injected,
    )
    return injected
