# Execution Plan — Chasm Refactoring + Opportunity Engine

*Generated after full codebase review*

---

## Part 1: Assessment of Existing Implementation Plans

After reviewing both `Implementation Plan` and `Combined Refactoring Plan`, here's what's **already done** vs. **still outstanding**:

### Already Completed

| Item | Evidence |
|------|----------|
| Centralized config via `pydantic-settings` | `chasm/core/config.py` uses `BaseSettings` with all paths, API keys, tuning params |
| API route modularization | `chasm/api/routes/` has `products.py`, `reports.py`, `onboarding.py`, `research.py`, `interviews.py` |
| Graph persistence decoupled | `chasm/graph/persistence.py` with `load_graph_from_disk()` / `save_graph_to_disk()` |
| `GeminiAgent` base class | `chasm/core/llm.py` — all agents inherit from it |
| Frontend env var config | `api.ts` uses `import.meta.env.VITE_API_URL` |
| Test files in `tests/` | `test_graph_builder.py`, `test_vector_engine.py`, `test_interviewer.py` exist |

### Still Outstanding (from Refactoring Plans)

| Item | Priority | Notes |
|------|----------|-------|
| **Dead code deletion** | High | Need to verify if `knowledge_graph.py`, `schemas.py`, `embeddings.py`, `orchestrator.py`, `readers.py` still exist |
| **Pipeline class refactor** | Medium | `run_weekly_research()` is still a monolithic function; should become `WeeklyResearchPipeline` class |
| **Component deduplication bug** | High | `extractor.py:191` creates a new `Component` node for every insight instead of reusing existing ones |
| **`_CATEGORY_MAP` duplication** | Low | Identical dict in both `extractor.py` and `interviewer.py` — should be in `schema.py` or a shared util |
| **UX prompts cleanup** | Medium | `App.tsx:83` uses `window.prompt()` / `window.alert()` for onboarding — should be proper modals |
| **CSS standardization** | Low | Mix of inline `style={{}}` objects and Tailwind utility classes |
| **`__main__` block cleanup** | Low | Need to verify if any remain in production code |

### Points of Agreement / Disagreement

I **agree** with all items in both plans. They're well-prioritized and the analysis is accurate. Two notes:

1. **Component deduplication** (item 5 in Combined Plan) is more critical than the plan implies — every insight currently creates a *new* Component node with a fresh UUID, meaning the graph has potentially hundreds of duplicate "Battery" components instead of one. This bloats the graph and breaks the Alignment Matrix aggregation. This should be **priority 1** for the refactoring work.

2. **Pipeline class refactor** is good engineering but lower urgency than the Opportunity Engine UI work. I'd suggest doing it *after* the frontend redesign ships, unless it blocks the new `/api/opportunities` endpoint.

---

## Part 2: Opportunity Engine — Execution Plan

This section covers the new feature work from the `project_overview.md` redesign spec.

### Phase 1: Backend Foundation (Do First)

#### 1A. Fix Component Deduplication (blocks everything)

**File:** `chasm/graph/builder.py`

Add a `find_or_create_component()` method that checks if a Component with the same `name` already exists under a given Product before creating a new node. Update `add_component()` to deduplicate by name+product.

**File:** `chasm/agents/extractor.py` + `chasm/agents/interviewer.py`

Update callers to use deduplication-aware graph methods or pass existing component IDs.

#### 1B. Add Opportunity & Persona Models

**File:** `chasm/models/schema.py`

Add new Pydantic models:

```python
class OpportunityType(str, Enum):
    UNMET_NEED = "Unmet Need"
    FRICTION_POINT = "Friction Point"
    REVENUE_RISK = "Revenue Risk"
    FEATURE_REQUEST = "Feature Request"

class Severity(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class Opportunity(BaseModel):
    id: str
    title: str
    opportunity_type: OpportunityType
    severity: Severity
    summary: str
    persona_tags: list[str]
    evidence_node_ids: list[str]  # Insight node IDs backing this
    product_id: str
    created_at: str

class Persona(BaseModel):
    id: str
    name: str              # e.g., "Mid-Market Sales Execs"
    description: str
    jobs_to_be_done: list[dict]  # [{title, evidence_ids, status}]
    product_id: str
```

#### 1C. Extend GraphSynthesizer → OpportunityGenerator

**File:** `chasm/agents/synthesizer.py` (new or extend existing)

Create an `OpportunityGenerator` agent (extends `GeminiAgent`) with a prompt that:
- Takes all component sentiment data + insight summaries for a product
- Returns typed `Opportunity` objects with evidence links (insight IDs)
- Returns `Persona` objects with JTBD derived from insight clustering

The prompt should instruct Gemini to:
1. Identify 5-10 opportunities (not just 3 discoveries)
2. Classify each by type and severity
3. Tag with customer persona segments
4. Link each to specific insight IDs as evidence

#### 1D. New API Endpoints

**File:** `chasm/api/routes/opportunities.py` (new)

```
GET  /api/opportunities/{product_id}     → list of Opportunity objects
POST /api/opportunities/{product_id}/generate  → trigger generation
```

**File:** `chasm/api/routes/personas.py` (new)

```
GET  /api/personas/{product_id}          → list of Persona objects with JTBD
```

**File:** `chasm/api/routes/products.py` (modify)

Add a subgraph endpoint:
```
GET  /api/graph/subgraph?node_ids=id1,id2,id3  → filtered GraphData
```

This powers the Evidence Drawer's scoped Galaxy Map.

Register new routers in `chasm/api/main.py`.

#### 1E. Storage

**Decision recommendation for Open Question #1:** Extend the existing graph with `Opportunity` and `Persona` node types rather than creating a Supabase table. This keeps everything in NetworkX and avoids a second data store dependency for the MVP. The graph already has the persistence layer (`export.json`). If scale becomes an issue later, migrate to Supabase.

Add to `ChasmGraph`:
- `add_opportunity(opportunity, product_id, evidence_insight_ids)`
- `add_persona(persona, product_id)`
- Query methods: `get_opportunities(product_id)`, `get_personas(product_id)`

#### 1F. Pipeline Step 8

**File:** `chasm/workflows/pipeline.py`

After semantic linking (step 5), add:
```python
# Step 6: Generate opportunities
opportunity_gen = OpportunityGenerator()
opportunities = opportunity_gen.generate(product_id, graph)
for opp in opportunities:
    graph.add_opportunity(opp, product_id, opp.evidence_node_ids)
```

---

### Phase 2: Frontend Redesign

#### 2A. New Types & API Functions

**File:** `chasm-ui/src/api.ts`

Add interfaces:
- `Opportunity` (mirrors backend model)
- `Persona` with `JobToBeDone[]`
- `fetchOpportunities(productId)`
- `fetchPersonas(productId)`
- `fetchSubgraph(nodeIds)`
- `generateOpportunities(productId)`

#### 2B. OpportunityFeed Component (New Default Home)

**File:** `chasm-ui/src/components/OpportunityFeed.tsx` (new)

- Prioritized vertical feed of opportunity cards
- Each card shows: title, type badge, severity indicator, persona tags, insight count
- "See Evidence" button on each card → opens Evidence Drawer
- Sort/filter controls: by severity, by type, by persona
- Empty state with CTA to trigger research

#### 2C. PersonaExplorer Component

**File:** `chasm-ui/src/components/PersonaExplorer.tsx` (new)

- Grid of persona cards (e.g., "Enterprise Admins", "SMB End Users")
- Click a persona → expands to show top 3 JTBD for that segment
- Each JTBD is clickable → opens Evidence Drawer
- Replaces AlignmentMatrix as the "who's affected?" view

#### 2D. EvidenceDrawer Component

**File:** `chasm-ui/src/components/EvidenceDrawer.tsx` (new)

- Slide-out panel (right side, over content)
- Top section: list of insight summaries with sentiment badges and source links
- Bottom section: scoped `GalaxyMap` showing only relevant subgraph nodes
- Close button returns to previous view
- Accepts `evidenceNodeIds: string[]` prop → fetches subgraph

#### 2E. Modify App.tsx

**File:** `chasm-ui/src/App.tsx`

- Change `ViewMode` to `'opportunities' | 'personas' | 'research'`
- Default to `'opportunities'` (was `'matrix'`)
- Replace Matrix/Galaxy toggle buttons with Opportunities/Personas/Research tabs
- Add Evidence Drawer state management (open/closed, current evidence IDs)
- Replace `window.prompt()` onboarding with a proper modal component

#### 2F. Modify StatsBar.tsx

**File:** `chasm-ui/src/components/StatsBar.tsx`

- Replace generic node/edge counts with opportunity-centric metrics:
  - "X Opportunities" (total)
  - "X High Severity" (count of high)
  - "X Personas"
  - "X Insights" (keep)

#### 2G. Deprecate Old Components

- `AlignmentMatrix.tsx` — remove import from App.tsx, keep file for reference
- `DiscoveriesPanel.tsx` — already absent from current code (was mentioned in overview but not in the repo)

---

### Phase 3: Refactoring Cleanup (Post-Ship)

These items from the refactoring plans should be done after the Opportunity Engine ships:

1. **Pipeline class refactor** — `WeeklyResearchPipeline` class with step methods
2. **Dead code deletion** — remove any leftover legacy files
3. **`_CATEGORY_MAP` deduplication** — move to shared location
4. **CSS standardization** — convert remaining inline styles to Tailwind
5. **Comprehensive test coverage** — add tests for new opportunity/persona endpoints

---

## Open Design Decisions — Recommendations

### Question 1: Supabase schema vs. graph storage
**Recommendation:** Store opportunities and personas as graph nodes in NetworkX for the MVP. This avoids adding Supabase write dependencies and keeps the single-source-of-truth in the graph. Add `node_type: "Opportunity"` and `node_type: "Persona"` alongside existing Product/Component/Insight/Source types.

### Question 2: Persona segmentation
**Recommendation:** LLM-generated personas from insight clustering. The `OpportunityGenerator` prompt should identify personas from patterns in the insight text (e.g., "enterprise users mention export frequently" → "Enterprise Power Users" persona). No manual tagging UI needed for v1. Add manual override later if users want to customize segments.

### Question 3: Old view retention
**Recommendation:** Remove Matrix and Galaxy as top-level tabs. The Galaxy Map lives on inside the Evidence Drawer (scoped subgraph view). The Matrix view can be fully removed — the Persona Explorer provides a better "who's affected?" answer. If users miss it, it can return as a settings-accessible "Advanced" view later.

---

## Execution Order Summary

```
1. Fix component deduplication bug (builder.py + extractor.py)
2. Add Opportunity/Persona models (schema.py)
3. Add graph methods for new node types (builder.py)
4. Build OpportunityGenerator agent (synthesizer.py)
5. Add API endpoints (routes/opportunities.py, routes/personas.py)
6. Add subgraph endpoint (routes/products.py)
7. Update pipeline with step 8 (pipeline.py)
8. Add frontend types + API functions (api.ts)
9. Build EvidenceDrawer component
10. Build OpportunityFeed component
11. Build PersonaExplorer component
12. Rewire App.tsx (new tabs, drawer state, remove old views)
13. Update StatsBar with opportunity metrics
14. Post-ship cleanup (pipeline refactor, dead code, tests)
```

Estimated file changes: **~8 modified files, ~5 new files**
