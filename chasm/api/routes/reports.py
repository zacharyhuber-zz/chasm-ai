"""Report-related API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from chasm.core.config import settings

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/reports/{product_id}")
def list_reports(product_id: str):
    """List available Monday Briefing reports for a product."""
    reports_dir = settings.reports_dir / product_id
    if not reports_dir.exists():
        return []

    reports: list[dict[str, str]] = []
    for md_file in sorted(reports_dir.glob("*.md"), reverse=True):
        reports.append({
            "filename": md_file.name,
            "product_id": product_id,
            "path": str(md_file),
        })
    return reports


@router.get("/reports/{product_id}/{filename}")
def get_report(product_id: str, filename: str):
    """Return the content of a specific report."""
    filepath = settings.reports_dir / product_id / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return {"content": filepath.read_text(encoding="utf-8")}
