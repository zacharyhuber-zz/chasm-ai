import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ProductNode {
    id: string;
    name: string;
    description?: string;
    url?: string;
}

export interface GraphNode {
    id: string;
    name?: string;
    node_type?: string;
    summary?: string;
    sentiment?: number;
    tags?: string[];
    category?: string;
    [key: string]: unknown;
}

export interface GraphLink {
    source: string;
    target: string;
    relation?: string;
    weight?: number;
}

export interface GraphData {
    nodes: GraphNode[];
    links: GraphLink[];
}

export interface ReportInfo {
    filename: string;
    product_id: string;
    path: string;
}

export interface ComponentSentiment {
    name: string;
    internalSentiment: number;
    externalSentiment: number;
    insightCount: number;
}

export async function fetchProducts(): Promise<ProductNode[]> {
    const res = await axios.get<ProductNode[]>(`${API_BASE}/api/products`);
    return res.data;
}

export async function fetchGraph(): Promise<GraphData> {
    const res = await axios.get<GraphData>(`${API_BASE}/api/graph`);
    return res.data;
}

export async function fetchReports(productId: string): Promise<ReportInfo[]> {
    const res = await axios.get<ReportInfo[]>(`${API_BASE}/api/reports/${productId}`);
    return res.data;
}

export async function onboardCompany(url: string): Promise<ProductNode[]> {
    const res = await axios.post<ProductNode[]>(`${API_BASE}/api/onboard`, { url });
    return res.data;
}

export async function triggerResearch(productId: string): Promise<{ status: string }> {
    const res = await axios.post<{ status: string }>(`${API_BASE}/api/research/${productId}`);
    return res.data;
}

/**
 * Derive per-component sentiment data from the graph for the Alignment Matrix.
 * Groups insights by their target component and separates internal vs external.
 */
export function deriveComponentSentiments(graph: GraphData): ComponentSentiment[] {
    const componentMap = new Map<string, { internal: number[]; external: number[] }>();

    // Build a quick node lookup
    const nodeById = new Map<string, GraphNode>();
    graph.nodes.forEach((n) => nodeById.set(n.id, n));

    // Find Insight → Component via ABOUT edges, Source → Insight via YIELDS
    const insightSources = new Map<string, string>(); // insightId → sourceType
    const insightTargets = new Map<string, string>(); // insightId → componentName

    graph.links.forEach((link) => {
        const src = typeof link.source === 'string' ? link.source : (link.source as any).id;
        const tgt = typeof link.target === 'string' ? link.target : (link.target as any).id;

        if (link.relation === 'YIELDS') {
            const sourceNode = nodeById.get(src);
            if (sourceNode) {
                const srcType = (sourceNode as any).type || (sourceNode as any).source_type || '';
                insightSources.set(tgt, srcType);
            }
        }
        if (link.relation === 'ABOUT') {
            const targetNode = nodeById.get(tgt);
            if (targetNode?.name) {
                insightTargets.set(src, targetNode.name);
            }
        }
    });

    // Aggregate by component
    graph.nodes.forEach((node) => {
        if (node.node_type !== 'Insight' || node.sentiment === undefined) return;

        const compName = insightTargets.get(node.id) || 'General';
        const srcType = insightSources.get(node.id) || '';

        if (!componentMap.has(compName)) {
            componentMap.set(compName, { internal: [], external: [] });
        }

        const bucket = componentMap.get(compName)!;
        if (srcType === 'Employee_Interview') {
            bucket.internal.push(node.sentiment);
        } else {
            bucket.external.push(node.sentiment);
        }
    });

    const avg = (arr: number[]) => (arr.length > 0 ? arr.reduce((a, b) => a + b, 0) / arr.length : 0);

    return Array.from(componentMap.entries()).map(([name, data]) => ({
        name,
        internalSentiment: parseFloat(avg(data.internal).toFixed(2)),
        externalSentiment: parseFloat(avg(data.external).toFixed(2)),
        insightCount: data.internal.length + data.external.length,
    }));
}

// ---------------------------------------------------------------------------
// Interview API
// ---------------------------------------------------------------------------

export interface InterviewSessionInfo {
    session_id: string;
    status: string;
    interview_url: string;
}

export interface InterviewMessage {
    role: string;
    content: string;
    timestamp?: string;
}

export interface InterviewDetail {
    session_id: string;
    status: string;
    messages: InterviewMessage[];
    created_at: string;
    completed_at?: string;
}

export interface InterviewResponse {
    role: string;
    content: string;
    is_complete: boolean;
}

export async function createInterviewSession(): Promise<InterviewSessionInfo> {
    const res = await axios.post<InterviewSessionInfo>(`${API_BASE}/api/interviews`);
    return res.data;
}

export async function getInterviewSession(sessionId: string): Promise<InterviewDetail> {
    const res = await axios.get<InterviewDetail>(`${API_BASE}/api/interviews/${sessionId}`);
    return res.data;
}

export async function sendInterviewMessage(
    sessionId: string,
    message: string,
): Promise<InterviewResponse> {
    const res = await axios.post<InterviewResponse>(
        `${API_BASE}/api/interviews/${sessionId}/message`,
        { message },
    );
    return res.data;
}

export async function completeInterview(
    sessionId: string,
): Promise<{ status: string; insights_extracted: number }> {
    const res = await axios.post<{ status: string; insights_extracted: number }>(
        `${API_BASE}/api/interviews/${sessionId}/complete`,
    );
    return res.data;
}
