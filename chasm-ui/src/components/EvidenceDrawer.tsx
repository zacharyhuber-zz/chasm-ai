import { useEffect, useState } from 'react';
import { X, ExternalLink, TrendingDown, TrendingUp, Minus } from 'lucide-react';
import { fetchSubgraph, type GraphData, type GraphNode } from '../api';
import GalaxyMap from './GalaxyMap';

interface EvidenceDrawerProps {
    evidenceNodeIds: string[];
    title: string;
    onClose: () => void;
}

export default function EvidenceDrawer({ evidenceNodeIds, title, onClose }: EvidenceDrawerProps) {
    const [subgraph, setSubgraph] = useState<GraphData | null>(null);
    const [insights, setInsights] = useState<GraphNode[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (evidenceNodeIds.length === 0) return;

        setLoading(true);
        fetchSubgraph(evidenceNodeIds)
            .then((data) => {
                setSubgraph(data);
                // Pull out insight nodes for the list
                const insightNodes = data.nodes.filter((n) => n.node_type === 'Insight');
                setInsights(insightNodes);
            })
            .catch(() => {
                setSubgraph({ nodes: [], links: [] });
                setInsights([]);
            })
            .finally(() => setLoading(false));
    }, [evidenceNodeIds]);

    return (
        <>
            {/* Backdrop */}
            <div
                onClick={onClose}
                style={{
                    position: 'fixed',
                    inset: 0,
                    background: 'rgba(0, 0, 0, 0.5)',
                    zIndex: 90,
                }}
            />

            {/* Drawer */}
            <div
                style={{
                    position: 'fixed',
                    top: 0,
                    right: 0,
                    width: 560,
                    maxWidth: '90vw',
                    height: '100vh',
                    background: 'linear-gradient(180deg, #0f1629 0%, #0a0e1a 100%)',
                    borderLeft: '1px solid #1e2547',
                    zIndex: 100,
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden',
                    animation: 'slideIn 0.25s ease-out',
                }}
            >
                {/* Header */}
                <div
                    style={{
                        padding: '20px 24px',
                        borderBottom: '1px solid #1e2547',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                    }}
                >
                    <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 10, fontWeight: 600, color: '#64748b', letterSpacing: '0.08em', marginBottom: 4 }}>
                            EVIDENCE
                        </div>
                        <h2 style={{ fontSize: 16, fontWeight: 700, color: '#e2e8f0', lineHeight: 1.3 }}>
                            {title}
                        </h2>
                    </div>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'rgba(100, 116, 139, 0.15)',
                            border: '1px solid #2a3154',
                            borderRadius: 8,
                            padding: 8,
                            cursor: 'pointer',
                            color: '#94a3b8',
                            display: 'flex',
                            alignItems: 'center',
                        }}
                    >
                        <X size={16} />
                    </button>
                </div>

                {/* Content */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px' }}>
                    {loading ? (
                        <div style={{ color: '#64748b', fontSize: 13, padding: 20, textAlign: 'center' }}>
                            Loading evidence...
                        </div>
                    ) : (
                        <>
                            {/* Insight list */}
                            <div style={{ fontSize: 10, fontWeight: 600, color: '#64748b', letterSpacing: '0.08em', marginBottom: 12 }}>
                                {insights.length} SUPPORTING INSIGHT{insights.length !== 1 ? 'S' : ''}
                            </div>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 24 }}>
                                {insights.map((insight) => (
                                    <InsightCard key={insight.id} insight={insight} />
                                ))}
                                {insights.length === 0 && (
                                    <div style={{ color: '#475569', fontSize: 13, padding: 12 }}>
                                        No insight data available for these evidence IDs.
                                    </div>
                                )}
                            </div>

                            {/* Scoped Galaxy Map */}
                            {subgraph && subgraph.nodes.length > 0 && (
                                <>
                                    <div style={{ fontSize: 10, fontWeight: 600, color: '#64748b', letterSpacing: '0.08em', marginBottom: 12 }}>
                                        KNOWLEDGE SUBGRAPH
                                    </div>
                                    <div style={{ height: 350 }}>
                                        <GalaxyMap graphData={subgraph} compact />
                                    </div>
                                </>
                            )}
                        </>
                    )}
                </div>
            </div>

            <style>{`
                @keyframes slideIn {
                    from { transform: translateX(100%); }
                    to { transform: translateX(0); }
                }
            `}</style>
        </>
    );
}

function InsightCard({ insight }: { insight: GraphNode }) {
    const sentiment = insight.sentiment ?? 0;
    const SentimentIcon = sentiment > 0.2 ? TrendingUp : sentiment < -0.2 ? TrendingDown : Minus;
    const sentimentColor = sentiment > 0.2 ? '#10b981' : sentiment < -0.2 ? '#f43f5e' : '#f59e0b';

    // Try to find a source URL from the node data
    const sourceUrl = (insight as any).url || null;

    return (
        <div
            className="glass-card"
            style={{ padding: '14px 16px' }}
        >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <div
                    style={{
                        width: 28,
                        height: 28,
                        borderRadius: 8,
                        background: `${sentimentColor}15`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        marginTop: 2,
                    }}
                >
                    <SentimentIcon size={14} color={sentimentColor} />
                </div>
                <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 13, color: '#e2e8f0', lineHeight: 1.5 }}>
                        {insight.summary}
                    </p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                        <span
                            style={{
                                fontSize: 11,
                                color: sentimentColor,
                                fontWeight: 600,
                            }}
                        >
                            {sentiment > 0 ? '+' : ''}{sentiment.toFixed(2)}
                        </span>
                        {insight.tags?.map((tag) => (
                            <span
                                key={tag}
                                style={{
                                    fontSize: 10,
                                    padding: '2px 8px',
                                    borderRadius: 6,
                                    background: 'rgba(59, 130, 246, 0.1)',
                                    color: '#94a3b8',
                                    border: '1px solid rgba(59, 130, 246, 0.2)',
                                }}
                            >
                                {tag}
                            </span>
                        ))}
                        {sourceUrl && (
                            <a
                                href={sourceUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{
                                    fontSize: 10,
                                    color: '#3b82f6',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 3,
                                    marginLeft: 'auto',
                                }}
                            >
                                Source <ExternalLink size={10} />
                            </a>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
