import { useEffect, useState } from 'react';
import {
    AlertTriangle,
    Zap,
    TrendingDown,
    Lightbulb,
    Eye,
    RefreshCw,
    Sparkles,
} from 'lucide-react';
import {
    fetchOpportunities,
    generateOpportunities,
    type Opportunity,
} from '../api';

const TYPE_CONFIG: Record<string, { icon: typeof Zap; color: string }> = {
    'Unmet Need': { icon: Lightbulb, color: '#8b5cf6' },
    'Friction Point': { icon: AlertTriangle, color: '#f59e0b' },
    'Revenue Risk': { icon: TrendingDown, color: '#f43f5e' },
    'Feature Request': { icon: Sparkles, color: '#3b82f6' },
};

const SEVERITY_COLORS: Record<string, string> = {
    High: '#f43f5e',
    Medium: '#f59e0b',
    Low: '#10b981',
};

interface OpportunityFeedProps {
    productId: string | null;
    onShowEvidence: (nodeIds: string[], title: string) => void;
}

export default function OpportunityFeed({ productId, onShowEvidence }: OpportunityFeedProps) {
    const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [filterType, setFilterType] = useState<string | null>(null);

    useEffect(() => {
        if (!productId) {
            setOpportunities([]);
            return;
        }
        setLoading(true);
        fetchOpportunities(productId)
            .then(setOpportunities)
            .catch(() => setOpportunities([]))
            .finally(() => setLoading(false));
    }, [productId]);

    const handleGenerate = async () => {
        if (!productId || generating) return;
        setGenerating(true);
        try {
            await generateOpportunities(productId);
            // Poll for results after a delay (generation happens in background)
            setTimeout(async () => {
                const opps = await fetchOpportunities(productId);
                setOpportunities(opps);
                setGenerating(false);
            }, 8000);
        } catch {
            setGenerating(false);
        }
    };

    const filtered = filterType
        ? opportunities.filter((o) => o.opportunity_type === filterType)
        : opportunities;

    if (!productId) {
        return (
            <div className="glass-card fade-in" style={{ padding: 40, textAlign: 'center' }}>
                <Zap size={32} color="#3b82f6" style={{ marginBottom: 12 }} />
                <h3 style={{ fontSize: 18, fontWeight: 700, color: '#e2e8f0', marginBottom: 8 }}>
                    Select a Product
                </h3>
                <p style={{ color: '#64748b', fontSize: 13 }}>
                    Choose a product from the sidebar to see its opportunities.
                </p>
            </div>
        );
    }

    return (
        <div className="fade-in">
            {/* Controls bar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
                {/* Type filters */}
                <button
                    onClick={() => setFilterType(null)}
                    style={{
                        padding: '6px 12px',
                        borderRadius: 8,
                        border: '1px solid #2a3154',
                        background: !filterType ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                        color: !filterType ? '#e2e8f0' : '#64748b',
                        fontSize: 12,
                        fontWeight: 500,
                        cursor: 'pointer',
                    }}
                >
                    All ({opportunities.length})
                </button>
                {Object.entries(TYPE_CONFIG).map(([type, config]) => {
                    const count = opportunities.filter((o) => o.opportunity_type === type).length;
                    if (count === 0) return null;
                    return (
                        <button
                            key={type}
                            onClick={() => setFilterType(filterType === type ? null : type)}
                            style={{
                                padding: '6px 12px',
                                borderRadius: 8,
                                border: `1px solid ${filterType === type ? config.color + '40' : '#2a3154'}`,
                                background: filterType === type ? config.color + '15' : 'transparent',
                                color: filterType === type ? '#e2e8f0' : '#64748b',
                                fontSize: 12,
                                fontWeight: 500,
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 4,
                            }}
                        >
                            <config.icon size={12} />
                            {type} ({count})
                        </button>
                    );
                })}

                {/* Generate button */}
                <button
                    onClick={handleGenerate}
                    disabled={generating}
                    style={{
                        marginLeft: 'auto',
                        padding: '6px 14px',
                        borderRadius: 8,
                        border: '1px solid rgba(139, 92, 246, 0.3)',
                        background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1))',
                        color: '#94a3b8',
                        fontSize: 12,
                        fontWeight: 500,
                        cursor: generating ? 'wait' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                    }}
                >
                    <RefreshCw size={12} className={generating ? 'animate-spin' : ''} />
                    {generating ? 'Generating...' : 'Generate Insights'}
                </button>
            </div>

            {/* Loading state */}
            {loading && (
                <div style={{ color: '#64748b', fontSize: 13, padding: 20, textAlign: 'center' }}>
                    Loading opportunities...
                </div>
            )}

            {/* Empty state */}
            {!loading && opportunities.length === 0 && (
                <div className="glass-card" style={{ padding: 40, textAlign: 'center' }}>
                    <Sparkles size={32} color="#8b5cf6" style={{ marginBottom: 12 }} />
                    <h3 style={{ fontSize: 16, fontWeight: 700, color: '#e2e8f0', marginBottom: 8 }}>
                        No Opportunities Yet
                    </h3>
                    <p style={{ color: '#64748b', fontSize: 13, marginBottom: 16 }}>
                        Run research first, then generate insights to discover opportunities.
                    </p>
                    <button
                        onClick={handleGenerate}
                        disabled={generating}
                        style={{
                            padding: '10px 20px',
                            borderRadius: 10,
                            border: 'none',
                            background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                            color: 'white',
                            fontSize: 13,
                            fontWeight: 600,
                            cursor: generating ? 'wait' : 'pointer',
                        }}
                    >
                        {generating ? 'Generating...' : 'Generate Insights'}
                    </button>
                </div>
            )}

            {/* Opportunity cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {filtered.map((opp) => (
                    <OpportunityCard
                        key={opp.id}
                        opportunity={opp}
                        onShowEvidence={() => onShowEvidence(opp.evidence_node_ids, opp.title)}
                    />
                ))}
            </div>
        </div>
    );
}

function OpportunityCard({
    opportunity,
    onShowEvidence,
}: {
    opportunity: Opportunity;
    onShowEvidence: () => void;
}) {
    const typeConfig = TYPE_CONFIG[opportunity.opportunity_type] || TYPE_CONFIG['Unmet Need'];
    const TypeIcon = typeConfig.icon;
    const severityColor = SEVERITY_COLORS[opportunity.severity] || '#64748b';

    return (
        <div className="glass-card" style={{ padding: '20px 24px' }}>
            {/* Top row: type + severity */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                <span
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                        fontSize: 11,
                        fontWeight: 600,
                        color: severityColor,
                        padding: '3px 8px',
                        borderRadius: 6,
                        background: severityColor + '15',
                        border: `1px solid ${severityColor}30`,
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                    }}
                >
                    <span style={{
                        width: 6,
                        height: 6,
                        borderRadius: '50%',
                        background: severityColor,
                    }} />
                    {opportunity.severity}
                </span>
                <span
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                        fontSize: 11,
                        fontWeight: 500,
                        color: typeConfig.color,
                        padding: '3px 8px',
                        borderRadius: 6,
                        background: typeConfig.color + '10',
                    }}
                >
                    <TypeIcon size={11} />
                    {opportunity.opportunity_type}
                </span>
            </div>

            {/* Title */}
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#e2e8f0', marginBottom: 6, lineHeight: 1.4 }}>
                {opportunity.title}
            </h3>

            {/* Summary */}
            <p style={{ fontSize: 13, color: '#94a3b8', lineHeight: 1.6, marginBottom: 12 }}>
                {opportunity.summary}
            </p>

            {/* Bottom row: personas + evidence link */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                {opportunity.persona_tags.map((tag) => (
                    <span
                        key={tag}
                        style={{
                            fontSize: 11,
                            padding: '3px 10px',
                            borderRadius: 6,
                            background: 'rgba(139, 92, 246, 0.1)',
                            color: '#a78bfa',
                            border: '1px solid rgba(139, 92, 246, 0.2)',
                        }}
                    >
                        {tag}
                    </span>
                ))}

                <button
                    onClick={onShowEvidence}
                    style={{
                        marginLeft: 'auto',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 5,
                        padding: '6px 12px',
                        borderRadius: 8,
                        border: '1px solid rgba(59, 130, 246, 0.3)',
                        background: 'rgba(59, 130, 246, 0.08)',
                        color: '#3b82f6',
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: 'pointer',
                    }}
                >
                    <Eye size={12} />
                    See Evidence ({opportunity.evidence_node_ids.length})
                </button>
            </div>
        </div>
    );
}
