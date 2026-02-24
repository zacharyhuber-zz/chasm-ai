import { useMemo } from 'react';
import {
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ReferenceLine,
    Label,
    Cell,
} from 'recharts';
import { Target } from 'lucide-react';
import type { ComponentSentiment } from '../api';

interface AlignmentMatrixProps {
    data: ComponentSentiment[];
    productName: string;
}


function getDotColor(item: ComponentSentiment): string {
    const x = item.internalSentiment;
    const y = item.externalSentiment;
    if (x > 0 && y < 0) return '#f43f5e'; // Blind Spot — rose
    if (x < 0 && y > 0) return '#f59e0b'; // Over-Engineered — amber
    if (x > 0 && y > 0) return '#10b981'; // Aligned Positive — emerald
    return '#8b5cf6'; // At Risk — purple
}

interface CustomTooltipProps {
    active?: boolean;
    payload?: Array<{
        payload: ComponentSentiment;
    }>;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
    if (!active || !payload?.[0]) return null;
    const d = payload[0].payload;
    return (
        <div className="glass-card" style={{ padding: '12px 16px', minWidth: 180 }}>
            <p style={{ fontWeight: 600, marginBottom: 4, color: '#e2e8f0' }}>{d.name}</p>
            <p style={{ color: '#94a3b8', fontSize: 13 }}>
                Internal: <span style={{ color: '#3b82f6' }}>{d.internalSentiment.toFixed(2)}</span>
            </p>
            <p style={{ color: '#94a3b8', fontSize: 13 }}>
                External: <span style={{ color: '#8b5cf6' }}>{d.externalSentiment.toFixed(2)}</span>
            </p>
            <p style={{ color: '#64748b', fontSize: 12, marginTop: 4 }}>
                {d.insightCount} insight{d.insightCount !== 1 ? 's' : ''}
            </p>
        </div>
    );
}

export default function AlignmentMatrix({ data, productName }: AlignmentMatrixProps) {
    // If no real data, show demo data
    const chartData = useMemo(() => {
        if (data.length > 0) return data;
        return [
            { name: 'Gimbal', internalSentiment: 0.6, externalSentiment: -0.5, insightCount: 12 },
            { name: 'Battery', internalSentiment: 0.3, externalSentiment: 0.7, insightCount: 8 },
            { name: 'Camera', internalSentiment: 0.8, externalSentiment: 0.6, insightCount: 15 },
            { name: 'Firmware', internalSentiment: -0.2, externalSentiment: -0.4, insightCount: 6 },
            { name: 'Propellers', internalSentiment: 0.5, externalSentiment: 0.2, insightCount: 4 },
            { name: 'Hinge', internalSentiment: 0.7, externalSentiment: -0.3, insightCount: 9 },
            { name: 'Landing Gear', internalSentiment: -0.3, externalSentiment: 0.4, insightCount: 3 },
        ];
    }, [data]);

    return (
        <div className="glass-card fade-in" style={{ padding: '28px 24px' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                <Target size={22} color="#8b5cf6" />
                <h2 style={{ fontSize: 20, fontWeight: 700, color: '#e2e8f0' }}>
                    Alignment Matrix
                </h2>
            </div>
            <p style={{ color: '#64748b', fontSize: 13, marginBottom: 24 }}>
                {productName || 'All Products'} — Internal vs. External sentiment by component
                {data.length === 0 && (
                    <span style={{ color: '#f59e0b', marginLeft: 8 }}>(demo data)</span>
                )}
            </p>

            {/* Quadrant Legend */}
            <div
                style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(4, 1fr)',
                    gap: 8,
                    marginBottom: 20,
                }}
            >
                {[
                    { label: 'Aligned', color: '#10b981', desc: 'Both positive' },
                    { label: 'Blind Spot', color: '#f43f5e', desc: 'Internal ↑ External ↓' },
                    { label: 'Over-Engineered', color: '#f59e0b', desc: 'Internal ↓ External ↑' },
                    { label: 'At Risk', color: '#8b5cf6', desc: 'Both negative' },
                ].map((q) => (
                    <div
                        key={q.label}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 6,
                            padding: '6px 10px',
                            borderRadius: 8,
                            background: 'rgba(255,255,255,0.03)',
                        }}
                    >
                        <div
                            style={{
                                width: 10,
                                height: 10,
                                borderRadius: '50%',
                                background: q.color,
                                flexShrink: 0,
                            }}
                        />
                        <div>
                            <div style={{ fontSize: 12, fontWeight: 600, color: '#e2e8f0' }}>{q.label}</div>
                            <div style={{ fontSize: 10, color: '#64748b' }}>{q.desc}</div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Chart */}
            <ResponsiveContainer width="100%" height={420}>
                <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 20 }}>
                    <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="rgba(42, 49, 84, 0.6)"
                        vertical={true}
                    />
                    <XAxis
                        type="number"
                        dataKey="internalSentiment"
                        domain={[-1, 1]}
                        tickCount={5}
                        tick={{ fill: '#64748b', fontSize: 11 }}
                        axisLine={{ stroke: '#2a3154' }}
                        tickLine={{ stroke: '#2a3154' }}
                    >
                        <Label
                            value="Internal Sentiment →"
                            position="bottom"
                            offset={0}
                            style={{ fill: '#94a3b8', fontSize: 12, fontWeight: 500 }}
                        />
                    </XAxis>
                    <YAxis
                        type="number"
                        dataKey="externalSentiment"
                        domain={[-1, 1]}
                        tickCount={5}
                        tick={{ fill: '#64748b', fontSize: 11 }}
                        axisLine={{ stroke: '#2a3154' }}
                        tickLine={{ stroke: '#2a3154' }}
                    >
                        <Label
                            value="External Sentiment →"
                            angle={-90}
                            position="left"
                            offset={0}
                            style={{ fill: '#94a3b8', fontSize: 12, fontWeight: 500 }}
                        />
                    </YAxis>

                    {/* Quadrant origin lines */}
                    <ReferenceLine x={0} stroke="#2a3154" strokeWidth={2} />
                    <ReferenceLine y={0} stroke="#2a3154" strokeWidth={2} />

                    {/* Quadrant labels */}
                    <ReferenceLine
                        x={0.55}
                        stroke="transparent"
                        label={{
                            value: '🎯 ALIGNED',
                            position: 'insideTop',
                            style: { fill: '#10b981', fontSize: 11, fontWeight: 600 },
                        }}
                    />
                    <ReferenceLine
                        x={0.5}
                        stroke="transparent"
                        label={{
                            value: '⚠️ BLIND SPOT',
                            position: 'insideBottom',
                            style: { fill: '#f43f5e', fontSize: 11, fontWeight: 600 },
                        }}
                    />
                    <ReferenceLine
                        x={-0.5}
                        stroke="transparent"
                        label={{
                            value: '🔧 OVER-ENGINEERED',
                            position: 'insideTop',
                            style: { fill: '#f59e0b', fontSize: 11, fontWeight: 600 },
                        }}
                    />
                    <ReferenceLine
                        x={-0.55}
                        stroke="transparent"
                        label={{
                            value: '🔴 AT RISK',
                            position: 'insideBottom',
                            style: { fill: '#8b5cf6', fontSize: 11, fontWeight: 600 },
                        }}
                    />

                    <Tooltip content={<CustomTooltip />} />

                    <Scatter data={chartData} fill="#3b82f6">
                        {chartData.map((entry, idx) => (
                            <Cell
                                key={`cell-${idx}`}
                                fill={getDotColor(entry)}
                                r={Math.max(6, Math.min(16, entry.insightCount * 1.2))}
                                stroke="rgba(255,255,255,0.2)"
                                strokeWidth={1}
                            />
                        ))}
                    </Scatter>
                </ScatterChart>
            </ResponsiveContainer>
        </div>
    );
}
