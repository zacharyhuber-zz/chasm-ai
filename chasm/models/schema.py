"""Pydantic schemas for the Chasm Hardware PLM Knowledge Graph.

Defines the core domain entities and their relationships:

    Product ──HAS_COMPONENT──▶ Component
    Insight ──RELATES_TO──────▶ Component | Product
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ComponentCategory(str, Enum):
    """Physical sub-system classification."""

    MECHANICAL = "Mechanical"
    ELECTRICAL = "Electrical"
    FIRMWARE = "Firmware"
    PACKAGING = "Packaging"
    UNKNOWN = "Unknown"


class SourceType(str, Enum):
    """Origin channel for ingested feedback."""

    WEBSITE = "Website"
    REDDIT = "Reddit"
    REVIEW = "Review"
    EMPLOYEE_INTERVIEW = "Employee_Interview"


# ---------------------------------------------------------------------------
# Core Entities
# ---------------------------------------------------------------------------

class Product(BaseModel):
    """The top-level device being analysed."""

    id: str = Field(..., description="Unique identifier for the product")
    name: str = Field(..., description="Human-readable product name")
    description: Optional[str] = Field(None, description="Brief product description")
    url: Optional[str] = Field(None, description="URL the product data was scraped from")


class Component(BaseModel):
    """A physical sub-system of a Product."""

    id: str = Field(..., description="Unique identifier for the component")
    name: str = Field(..., description="Component name (e.g. 'Battery Module')")
    category: ComponentCategory = Field(
        ...,
        description="Sub-system classification",
    )


class Source(BaseModel):
    """Origin record for a piece of ingested feedback."""

    id: str = Field(..., description="Unique identifier for the source")
    type: SourceType = Field(..., description="Channel the feedback came from")
    raw_text: str = Field(..., description="Original, unprocessed feedback text")
    url: Optional[str] = Field(None, description="Permalink to the source material")


class Insight(BaseModel):
    """A single actionable insight extracted from a Source."""

    id: str = Field(..., description="Unique identifier for the insight")
    summary: str = Field(..., description="Concise description of the feedback")
    sentiment: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Sentiment score from -1.0 (negative) to 1.0 (positive)",
    )
    tags: list[str] = Field(default_factory=list, description="Free-form topic tags")
    embedding: Optional[list[float]] = Field(
        None,
        description="Vector embedding for semantic similarity",
    )


# ---------------------------------------------------------------------------
# Opportunity Engine Entities
# ---------------------------------------------------------------------------

class OpportunityType(str, Enum):
    """Classification of a product opportunity."""

    UNMET_NEED = "Unmet Need"
    FRICTION_POINT = "Friction Point"
    REVENUE_RISK = "Revenue Risk"
    FEATURE_REQUEST = "Feature Request"


class Severity(str, Enum):
    """Priority level for an opportunity."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Opportunity(BaseModel):
    """A discrete, actionable product opportunity backed by graph evidence."""

    id: str = Field(..., description="Unique identifier for the opportunity")
    title: str = Field(..., description="Short description of the opportunity")
    opportunity_type: OpportunityType = Field(..., description="Classification")
    severity: Severity = Field(..., description="Priority level")
    summary: str = Field(..., description="Detailed explanation")
    persona_tags: list[str] = Field(
        default_factory=list,
        description="Customer segments affected",
    )
    evidence_node_ids: list[str] = Field(
        default_factory=list,
        description="Insight node IDs backing this opportunity",
    )
    product_id: str = Field(..., description="Product this opportunity belongs to")
    created_at: str = Field(..., description="ISO timestamp of creation")


class JobToBeDone(BaseModel):
    """A task a persona segment is struggling to complete."""

    title: str = Field(..., description="Short description of the job")
    status: str = Field(
        default="underserved",
        description="underserved | partially_met | well_served",
    )
    evidence_node_ids: list[str] = Field(
        default_factory=list,
        description="Insight node IDs supporting this job",
    )


class Persona(BaseModel):
    """A customer segment derived from insight clustering."""

    id: str = Field(..., description="Unique identifier for the persona")
    name: str = Field(..., description="Segment name (e.g., 'Enterprise Admins')")
    description: str = Field(..., description="Brief description of this segment")
    jobs_to_be_done: list[JobToBeDone] = Field(
        default_factory=list,
        description="Top jobs this segment is trying to accomplish",
    )
    product_id: str = Field(..., description="Product this persona relates to")
