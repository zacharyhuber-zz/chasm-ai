import { useEffect, useState } from 'react';
import { Users, ChevronDown, ChevronUp, Eye, CircleDot } from 'lucide-react';
import { fetchPersonas, type Persona, type JobToBeDone } from '../api';

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
    underserved: { label: 'Underserved', color: '#f43f5e' },
    partially_met: { label: 'Partially Met', color: '#f59e0b' },
    well_served: { label: 'Well Served', color: '#10b981' },
};

interface PersonaExplorerProps {
    productId: string | null;
    onShowEvidence: (nodeIds: string[], title: string) => void;
}

export default function PersonaExplorer({ productId, onShowEvidence }: PersonaExplorerProps) {
    const [personas, setPersonas] = useState<Persona[]>([]);
    const [loading, setLoading] = useState(false);
    const [expandedId, setExpandedId] = useState<string | null>(null);

    useEffect(() => {
        if (!productId) {
            setPersonas([]);
            return;
        }
        setLoading(true);
        fetchPersonas(productId)
            .then(setPersonas)
            .catch(() => setPersonas([]))
            .finally(() => setLoading(false));
    }, [productId]);

    if (!productId) {
        return (
            <div className="glass-card fade-in" style={{ padding: 40, textAlign: 'center' }}>
                <Users size={32} color="#8b5cf6" style={{ marginBottom: 12 }} />
                <h3 style={{ fontSize: 18, fontWeight: 700, color: '#e2e8f0', marginBottom: 8 }}>
                    Select a Product
                </h3>
                <p style={{ color: '#64748b', fontSize: 13 }}>
                    Choose a product from the sidebar to explore its customer personas.
                </p>
            </div>
        );
    }

    if (loading) {
        return (
            <div style={{ color: '#64748b', fontSize: 13, padding: 20, textAlign: 'center' }}>
                Loading personas...
            </div>
        );
    }

    if (personas.length === 0) {
        return (
            <div className="glass-card fade-in" style={{ padding: 40, textAlign: 'center' }}>
                <Users size={32} color="#64748b" style={{ marginBottom: 12 }} />
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#e2e8f0', marginBottom: 8 }}>
                    No Personas Yet
                </h3>
                <p style={{ color: '#64748b', fontSize: 13 }}>
                    Generate insights from the Opportunities tab to discover customer personas.
                </p>
            </div>
        );
    }

    return (
        <div className="fade-in">
            <div
                style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
                    gap: 12,
                }}
            >
                {personas.map((persona) => {
                    const isExpanded = expandedId === persona.id;
                    return (
                        <div
                            key={persona.id}
                            className="glass-card"
                            style={{
                                padding: '20px 24px',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                            }}
                            onClick={() => setExpandedId(isExpanded ? null : persona.id)}
                        >
                            {/* Header */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                                <div
                                    style={{
                                        width: 40,
                                        height: 40,
                                        borderRadius: 10,
                                        background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(59, 130, 246, 0.15))',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        flexShrink: 0,
                                    }}
                                >
                                    <Users size={18} color="#a78bfa" />
                                </div>
                                <div style={{ flex: 1 }}>
                                    <h3 style={{ fontSize: 15, fontWeight: 700, color: '#e2e8f0' }}>
                                        {persona.name}
                                    </h3>
                                    <p style={{ fontSize: 12, color: '#64748b' }}>
                                        {persona.jobs_to_be_done.length} job{persona.jobs_to_be_done.length !== 1 ? 's' : ''} to be done
                                    </p>
                                </div>
                                {isExpanded ? (
                                    <ChevronUp size={16} color="#64748b" />
                                ) : (
                                    <ChevronDown size={16} color="#64748b" />
                                )}
                            </div>

                            {/* Description */}
                            <p style={{ fontSize: 13, color: '#94a3b8', lineHeight: 1.5, marginBottom: isExpanded ? 16 : 0 }}>
                                {persona.description}
                            </p>

                            {/* Expanded: Jobs to be done */}
                            {isExpanded && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                    {persona.jobs_to_be_done.map((job, i) => (
                                        <JobCard
                                            key={i}
                                            job={job}
                                            personaName={persona.name}
                                            onShowEvidence={onShowEvidence}
                                        />
                                    ))}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function JobCard({
    job,
    personaName,
    onShowEvidence,
}: {
    job: JobToBeDone;
    personaName: string;
    onShowEvidence: (nodeIds: string[], title: string) => void;
}) {
    const statusConfig = STATUS_CONFIG[job.status] || STATUS_CONFIG.underserved;

    return (
        <div
            style={{
                padding: '12px 14px',
                borderRadius: 10,
                background: 'rgba(10, 14, 26, 0.5)',
                border: '1px solid #1e2547',
            }}
            onClick={(e) => e.stopPropagation()}
        >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <CircleDot size={12} color={statusConfig.color} />
                <span
                    style={{
                        fontSize: 10,
                        fontWeight: 600,
                        color: statusConfig.color,
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                    }}
                >
                    {statusConfig.label}
                </span>
            </div>

            <p style={{ fontSize: 13, color: '#e2e8f0', fontWeight: 500, marginBottom: 8, lineHeight: 1.4 }}>
                {job.title}
            </p>

            {job.evidence_node_ids.length > 0 && (
                <button
                    onClick={() =>
                        onShowEvidence(
                            job.evidence_node_ids,
                            `${personaName}: ${job.title}`,
                        )
                    }
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4,
                        padding: '4px 10px',
                        borderRadius: 6,
                        border: '1px solid rgba(59, 130, 246, 0.25)',
                        background: 'rgba(59, 130, 246, 0.06)',
                        color: '#3b82f6',
                        fontSize: 11,
                        fontWeight: 600,
                        cursor: 'pointer',
                    }}
                >
                    <Eye size={10} />
                    Evidence ({job.evidence_node_ids.length})
                </button>
            )}
        </div>
    );
}
