"""Interview API routes — session management and conversational interface."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from chasm.api.deps import get_graph
from chasm.agents.interviewer import Interviewer
from chasm.core.logger import get_logger
from chasm.interviews.sessions import (
    ChatMessage,
    create_session,
    load_session,
    save_session,
    complete_session,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["interviews"])

# Cache the Interviewer agent so we don't re-init on every request
_interviewer: Interviewer | None = None


def _get_interviewer() -> Interviewer:
    global _interviewer
    if _interviewer is None:
        _interviewer = Interviewer()
    return _interviewer


def _get_product_names() -> str:
    """Get a comma-separated list of all product names from the graph."""
    graph = get_graph()
    names = [
        data.get("name", nid)
        for nid, data in graph.graph.nodes(data=True)
        if data.get("node_type") == "Product"
    ]
    return ", ".join(names) if names else "the company's products"


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SessionOut(BaseModel):
    session_id: str
    status: str
    interview_url: str


class MessageRequest(BaseModel):
    message: str


class MessageOut(BaseModel):
    role: str
    content: str
    is_complete: bool = False


class SessionDetailOut(BaseModel):
    session_id: str
    status: str
    messages: list[dict]
    created_at: str
    completed_at: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/interviews", response_model=SessionOut)
def create_interview():
    """Create a new interview session and return its shareable URL."""
    session = create_session()

    return SessionOut(
        session_id=session.id,
        status=session.status,
        interview_url=f"/interview/{session.id}",
    )


@router.get("/interviews/{session_id}", response_model=SessionDetailOut)
def get_interview(session_id: str):
    """Get full session details including conversation history."""
    session = load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")

    return SessionDetailOut(
        session_id=session.id,
        status=session.status,
        messages=[m.model_dump() for m in session.messages],
        created_at=session.created_at,
        completed_at=session.completed_at,
    )


@router.post("/interviews/{session_id}/message", response_model=MessageOut)
def send_message(session_id: str, req: MessageRequest):
    """Send a user message and get the AI interviewer's response."""
    session = load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    if session.status == "completed":
        raise HTTPException(status_code=400, detail="This interview has already been completed")

    interviewer = _get_interviewer()
    product_names = _get_product_names()

    # If this is the first message, start the interview
    if session.status == "pending":
        greeting = interviewer.start_interview(product_names)
        session.status = "active"
        session.messages.append(ChatMessage(role="assistant", content=greeting))
        save_session(session)

        # Now process the user's actual message as a follow-up
        # (unless the "message" is empty — meaning they just want the greeting)
        if not req.message.strip():
            return MessageOut(role="assistant", content=greeting, is_complete=False)

    # Append the user's message
    session.messages.append(ChatMessage(role="user", content=req.message))

    # Build conversation history for the LLM
    history = [{"role": m.role, "content": m.content} for m in session.messages]

    # Get AI response
    ai_response = interviewer.next_turn(history, product_names)

    # Check if the interview is wrapping up
    is_complete = "thank you for your time" in ai_response.lower()

    session.messages.append(ChatMessage(role="assistant", content=ai_response))
    save_session(session)

    # Auto-complete if the AI wrapped up
    if is_complete:
        injected = complete_session(session)
        logger.info(
            "Interview %s auto-completed: %d insights injected.",
            session_id,
            injected,
        )

    return MessageOut(role="assistant", content=ai_response, is_complete=is_complete)


@router.post("/interviews/{session_id}/complete")
def end_interview(session_id: str):
    """Manually end an interview early and extract insights."""
    session = load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    if session.status == "completed":
        return {"status": "already_completed", "session_id": session_id}

    injected = complete_session(session)
    return {
        "status": "completed",
        "session_id": session_id,
        "insights_extracted": injected,
    }
