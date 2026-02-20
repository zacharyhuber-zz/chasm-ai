import { Activity, Box, GitBranch, Lightbulb } from 'lucide-react';

interface StatsBarProps {
    nodeCount: number;
    edgeCount: number;
    productCount: number;
    insightCount: number;
}

export default function StatsBar({ nodeCount, edgeCount, productCount, insightCount }: StatsBarProps) {
    const stats = [
        { label: 'Products', value: productCount, icon: Box, color: '#3b82f6' },
        { label: 'Insights', value: insightCount, icon: Lightbulb, color: '#f59e0b' },
        { label: 'Nodes', value: nodeCount, icon: Activity, color: '#10b981' },
        { label: 'Edges', value: edgeCount, icon: GitBranch, color: '#8b5cf6' },
    ];

    return (
        <div
            style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: 12,
                marginBottom: 24,
            }}
        >
            {stats.map((stat) => (
                <div
                    key={stat.label}
                    className="glass-card fade-in"
                    style={{
                        padding: '18px 20px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 14,
                    }}
                >
                    <div
                        style={{
                            width: 42,
                            height: 42,
                            borderRadius: 12,
                            background: `${stat.color}15`,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0,
                        }}
                    >
                        <stat.icon size={20} color={stat.color} />
                    </div>
                    <div>
                        <div style={{ fontSize: 24, fontWeight: 700, color: '#e2e8f0', lineHeight: 1 }}>
                            {stat.value.toLocaleString()}
                        </div>
                        <div style={{ fontSize: 12, color: '#64748b', fontWeight: 500, marginTop: 2 }}>
                            {stat.label}
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}
