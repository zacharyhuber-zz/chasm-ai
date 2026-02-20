"""Onboarding-related API routes."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from chasm.agents.cataloger import ProductCataloger
from chasm.api.deps import get_graph
from chasm.graph.persistence import save_graph_to_disk
from chasm.models.schema import Product

router = APIRouter(prefix="/api", tags=["onboarding"])


class OnboardRequest(BaseModel):
    url: str


class ProductOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    url: str | None = None


@router.post("/onboard", response_model=list[ProductOut])
def onboard_company(req: OnboardRequest):
    """Scrape a company website and return discovered products."""
    from fastapi import HTTPException

    cataloger = ProductCataloger()

    try:
        site_text = cataloger.scrape_company_site(req.url)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    products = cataloger.extract_products(site_text, req.url)

    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "url": p.url,
        }
        for p in products
    ]


class SelectProductsRequest(BaseModel):
    products: list[ProductOut]


@router.post("/onboard/confirm")
def confirm_onboarding(req: SelectProductsRequest):
    """Add user-selected products to the Knowledge Graph."""
    graph = get_graph()
    added: list[str] = []
    for p in req.products:
        product = Product(
            id=p.id,
            name=p.name,
            description=p.description,
            url=p.url,
        )
        graph.add_product(product)
        added.append(p.name)

    save_graph_to_disk(graph)
    return {
        "status": "ok",
        "added": added,
        "graph_nodes": graph.node_count,
        "graph_edges": graph.edge_count,
    }
