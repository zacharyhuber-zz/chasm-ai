import { useCallback, useEffect, useRef, useState } from 'react';
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d';
import { Orbit } from 'lucide-react';
import type { GraphData, GraphNode } from '../api';

/* ─── Color palette by node type ─── */
const NODE_COLORS: Record<string, string> = {
    Product: '#3b82f6',
    Component: '#10b981',
    Insight: '#f59e0b',
    Source: '#8b5cf6',
};

const NODE_SIZES: Record<string, number> = {
    Product: 8,
    Component: 6,
    Insight: 5,
    Source: 4,
};

interface GalaxyMapProps {
    graphData: GraphData | null;
}

export default function GalaxyMap({ graphData }: GalaxyMapProps) {
    const fgRef = useRef<ForceGraphMethods | undefined>(undefined);
    const containerRef = useRef<HTMLDivElement>(null);
    const [dimensions, setDimensions] = useState({ width: 800, height: 500 });
    const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set());
    const [highlightLinks, setHighlightLinks] = useState<Set<string>>(new Set());
    const [hoverNode, setHoverNode] = useState<GraphNode | null>(null);
    const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

    // Responsive sizing
    useEffect(() => {
        const updateSize = () => {
            if (containerRef.current) {
                setDimensions({
                    width: containerRef.current.offsetWidth,
                    height: Math.max(520, window.innerHeight - 260),
                });
            }
        };
        updateSize();
        window.addEventListener('resize', updateSize);
        return () => window.removeEventListener('resize', updateSize);
    }, []);

    // Build graph data for the force graph
    const forceData = useCallback(() => {
        if (!graphData || graphData.nodes.length === 0) {
            // Demo data
            return {
                nodes: [
                    { id: 'p1', name: 'DJI Mavic 3', node_type: 'Product' },
                    { id: 'c1', name: 'Gimbal', node_type: 'Component' },
                    { id: 'c2', name: 'Battery', node_type: 'Component' },
                    { id: 'c3', name: 'Camera', node_type: 'Component' },
                    { id: 'c4', name: 'Firmware', node_type: 'Component' },
                    { id: 'i1', name: 'Insight', node_type: 'Insight', summary: 'Gimbal wobbles in windy conditions' },
                    { id: 'i2', name: 'Insight', node_type: 'Insight', summary: 'Battery lasts 40+ minutes' },
                    { id: 'i3', name: 'Insight', node_type: 'Insight', summary: 'Camera quality is outstanding' },
                    { id: 'i4', name: 'Insight', node_type: 'Insight', summary: 'Gimbal motor seems under-specced' },
                    { id: 'i5', name: 'Insight', node_type: 'Insight', summary: 'Firmware v2.3 introduced UI lag' },
                    { id: 's1', name: 'r/dji', node_type: 'Source' },
                    { id: 's2', name: 'rtings.com', node_type: 'Source' },
                ],
                links: [
                    { source: 'p1', target: 'c1', relation: 'HAS_COMPONENT' },
                    { source: 'p1', target: 'c2', relation: 'HAS_COMPONENT' },
                    { source: 'p1', target: 'c3', relation: 'HAS_COMPONENT' },
                    { source: 'p1', target: 'c4', relation: 'HAS_COMPONENT' },
                    { source: 's1', target: 'i1', relation: 'YIELDS' },
                    { source: 's1', target: 'i4', relation: 'YIELDS' },
                    { source: 's2', target: 'i2', relation: 'YIELDS' },
                    { source: 's2', target: 'i3', relation: 'YIELDS' },
                    { source: 's1', target: 'i5', relation: 'YIELDS' },
                    { source: 'i1', target: 'c1', relation: 'ABOUT' },
                    { source: 'i2', target: 'c2', relation: 'ABOUT' },
                    { source: 'i3', target: 'c3', relation: 'ABOUT' },
                    { source: 'i4', target: 'c1', relation: 'ABOUT' },
                    { source: 'i5', target: 'c4', relation: 'ABOUT' },
                    { source: 'i1', target: 'i4', relation: 'SEMANTIC_MATCH' },
                ],
            };
        }
        return graphData;
    }, [graphData])();

    // Click handler — center + highlight neighbors
    const handleNodeClick = useCallback(
        (node: any) => {
            const fg = fgRef.current;
            if (fg && node.x !== undefined && node.y !== undefined) {
                fg.centerAt(node.x, node.y, 800);
                fg.zoom(3, 800);
            }

            const newHighlightNodes = new Set<string>();
            const newHighlightLinks = new Set<string>();

            newHighlightNodes.add(node.id);

            forceData.links.forEach((link: any) => {
                const srcId = typeof link.source === 'object' ? link.source.id : link.source;
                const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
                if (srcId === node.id || tgtId === node.id) {
                    newHighlightNodes.add(srcId);
                    newHighlightNodes.add(tgtId);
                    newHighlightLinks.add(`${srcId}->${tgtId}`);
                }
            });

            setHighlightNodes(newHighlightNodes);
            setHighlightLinks(newHighlightLinks);
        },
        [forceData],
    );

    // Hover handler for tooltip
    const handleNodeHover = useCallback((node: any, prevNode: any) => {
        if (node && node.node_type === 'Insight' && node.summary) {
            setHoverNode(node);
        } else {
            setHoverNode(null);
        }
        // Change cursor
        const el = document.querySelector('.force-graph-container canvas');
        if (el) {
            (el as HTMLElement).style.cursor = node ? 'pointer' : 'default';
        }
    }, []);

    const handleBackgroundClick = useCallback(() => {
        setHighlightNodes(new Set());
        setHighlightLinks(new Set());
        const fg = fgRef.current;
        if (fg) fg.zoom(1, 600);
    }, []);

    return (
        <div className="glass-card fade-in" style={{ padding: '28px 24px', overflow: 'hidden' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                <Orbit size={22} color="#3b82f6" />
                <h2 style={{ fontSize: 20, fontWeight: 700 }}>Galaxy Map</h2>
            </div>
            <p style={{ color: '#64748b', fontSize: 13, marginBottom: 16 }}>
                Knowledge Graph — interactive force-directed layout
                {(!graphData || graphData.nodes.length === 0) && (
                    <span style={{ color: '#f59e0b', marginLeft: 8 }}>(demo data)</span>
                )}
            </p>

            {/* Legend */}
            <div style={{ display: 'flex', gap: 16, marginBottom: 16, flexWrap: 'wrap' }}>
                {Object.entries(NODE_COLORS).map(([type, color]) => (
                    <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div
                            style={{
                                width: 10,
                                height: 10,
                                borderRadius: '50%',
                                background: color,
                                boxShadow: `0 0 6px ${color}60`,
                            }}
                        />
                        <span style={{ fontSize: 12, color: '#94a3b8' }}>{type}</span>
                    </div>
                ))}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div
                        style={{
                            width: 20,
                            height: 0,
                            borderTop: '2px dashed #f59e0b',
                        }}
                    />
                    <span style={{ fontSize: 12, color: '#94a3b8' }}>Semantic Match</span>
                </div>
            </div>

            {/* Graph container */}
            <div
                ref={containerRef}
                className="force-graph-container"
                style={{
                    borderRadius: 12,
                    overflow: 'hidden',
                    background: 'rgba(10, 14, 26, 0.8)',
                    border: '1px solid #1e2547',
                    position: 'relative',
                }}
                onMouseMove={(e) => {
                    const rect = containerRef.current?.getBoundingClientRect();
                    if (rect) {
                        setTooltipPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
                    }
                }}
            >
                <ForceGraph2D
                    ref={fgRef as any}
                    graphData={forceData}
                    width={dimensions.width - 50}
                    height={dimensions.height}
                    backgroundColor="transparent"
                    nodeLabel=""
                    nodeCanvasObject={(node: any, ctx, globalScale) => {
                        const type = node.node_type || 'Source';
                        const color = NODE_COLORS[type] || '#64748b';
                        const size = NODE_SIZES[type] || 4;
                        const isHighlighted = highlightNodes.size === 0 || highlightNodes.has(node.id);
                        const alpha = isHighlighted ? 1 : 0.15;

                        // Glow
                        if (isHighlighted && highlightNodes.size > 0) {
                            ctx.beginPath();
                            ctx.arc(node.x!, node.y!, size + 4, 0, 2 * Math.PI);
                            ctx.fillStyle = `${color}30`;
                            ctx.fill();
                        }

                        // Circle
                        ctx.beginPath();
                        ctx.arc(node.x!, node.y!, size, 0, 2 * Math.PI);
                        ctx.fillStyle = `${color}${Math.round(alpha * 255).toString(16).padStart(2, '0')}`;
                        ctx.fill();
                        ctx.strokeStyle = `${color}${Math.round(alpha * 180).toString(16).padStart(2, '0')}`;
                        ctx.lineWidth = 1;
                        ctx.stroke();

                        // Label
                        if (globalScale > 1.5 || type === 'Product' || (highlightNodes.has(node.id) && highlightNodes.size > 0)) {
                            const label = node.name || node.id;
                            const fontSize = type === 'Product' ? 12 / globalScale : 10 / globalScale;
                            ctx.font = `${type === 'Product' ? 'bold ' : ''}${fontSize}px Inter, sans-serif`;
                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'middle';
                            ctx.fillStyle = `rgba(226, 232, 240, ${alpha})`;
                            ctx.fillText(label, node.x!, node.y! + size + fontSize + 2);
                        }
                    }}
                    linkCanvasObject={(link: any, ctx) => {
                        const srcId = typeof link.source === 'object' ? link.source.id : link.source;
                        const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
                        const linkKey = `${srcId}->${tgtId}`;
                        const isHighlighted = highlightLinks.size === 0 || highlightLinks.has(linkKey);
                        const isSemantic = link.relation === 'SEMANTIC_MATCH';

                        const sx = typeof link.source === 'object' ? link.source.x : 0;
                        const sy = typeof link.source === 'object' ? link.source.y : 0;
                        const tx = typeof link.target === 'object' ? link.target.x : 0;
                        const ty = typeof link.target === 'object' ? link.target.y : 0;

                        ctx.beginPath();
                        if (isSemantic) {
                            ctx.setLineDash([4, 4]);
                            ctx.strokeStyle = isHighlighted ? '#f59e0b88' : '#f59e0b18';
                            ctx.lineWidth = isHighlighted ? 1.5 : 0.5;
                        } else {
                            ctx.setLineDash([]);
                            ctx.strokeStyle = isHighlighted ? '#2a315488' : '#2a315422';
                            ctx.lineWidth = isHighlighted ? 1 : 0.5;
                        }
                        ctx.moveTo(sx, sy);
                        ctx.lineTo(tx, ty);
                        ctx.stroke();
                        ctx.setLineDash([]);
                    }}
                    onNodeClick={handleNodeClick}
                    onNodeHover={handleNodeHover}
                    onBackgroundClick={handleBackgroundClick}
                    cooldownTicks={100}
                    d3AlphaDecay={0.02}
                    d3VelocityDecay={0.3}
                />

                {/* Tooltip */}
                {hoverNode && (
                    <div
                        style={{
                            position: 'absolute',
                            left: tooltipPos.x + 12,
                            top: tooltipPos.y - 40,
                            pointerEvents: 'none',
                            background: 'linear-gradient(135deg, rgba(26, 31, 54, 0.95), rgba(17, 24, 39, 0.9))',
                            backdropFilter: 'blur(12px)',
                            border: '1px solid #2a3154',
                            borderRadius: 10,
                            padding: '10px 14px',
                            maxWidth: 260,
                            zIndex: 50,
                        }}
                    >
                        <p style={{ fontSize: 10, color: '#64748b', marginBottom: 4, fontWeight: 600 }}>
                            INSIGHT
                        </p>
                        <p style={{ fontSize: 13, color: '#e2e8f0', lineHeight: 1.4 }}>
                            {(hoverNode as any).summary}
                        </p>
                    </div>
                )}
            </div>

            <p style={{ color: '#475569', fontSize: 11, marginTop: 10, textAlign: 'center' }}>
                Click a node to focus · Click background to reset · Scroll to zoom
            </p>
        </div>
    );
}
