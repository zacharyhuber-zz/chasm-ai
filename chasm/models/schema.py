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
